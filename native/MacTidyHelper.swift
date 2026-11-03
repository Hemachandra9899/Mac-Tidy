// Native helper for Mac Tidy. Prints one JSON object to stdout.
//
//   mac-tidy-helper reveal <path>
//   mac-tidy-helper trash <path> <dev> <inode> <mtime-ns> <size>
//   mac-tidy-helper space <volume-path>                    (free space, including purgeable)
//   mac-tidy-helper icon <output.png> [sf-symbol-name]   (development: export UI icons)

import AppKit
import Darwin
import Foundation

struct HelperError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

func respond(_ data: [String: Any]) {
    let value = try! JSONSerialization.data(withJSONObject: data)
    print(String(data: value, encoding: .utf8)!)
}

/// Must produce the same values as Python's `identity()` in trash.py.
func fingerprint(_ path: String) throws -> [String] {
    var info = stat()
    guard lstat(path, &info) == 0 else { throw HelperError(message: "Item no longer exists") }
    let mtime = Int64(info.st_mtimespec.tv_sec) * 1_000_000_000 + Int64(info.st_mtimespec.tv_nsec)
    return [String(info.st_dev), String(info.st_ino), String(mtime), String(info.st_size)]
}

func exportIcon(to output: String, symbol name: String) throws {
    guard let symbol = NSImage(systemSymbolName: name, accessibilityDescription: nil) else {
        throw HelperError(message: "Unknown SF Symbol: \(name)")
    }
    let image = NSImage(size: NSSize(width: 64, height: 64))
    image.lockFocus()
    let ratio = min(48 / symbol.size.width, 48 / symbol.size.height)
    let width = symbol.size.width * ratio
    let height = symbol.size.height * ratio
    symbol.draw(in: NSRect(x: (64 - width) / 2, y: (64 - height) / 2, width: width, height: height))
    image.unlockFocus()
    guard let tiff = image.tiffRepresentation,
          let png = NSBitmapImageRep(data: tiff)?.representation(using: .png, properties: [:])
    else { throw HelperError(message: "Could not render the icon") }
    try png.write(to: URL(fileURLWithPath: output))
}

func reveal(_ path: String) throws {
    guard FileManager.default.fileExists(atPath: path) else {
        throw HelperError(message: "Item no longer exists")
    }
    NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
}

/// "Important usage" capacity counts space macOS can purge on demand (iCloud
/// copies, caches, snapshots), which plain available capacity does not.
func volumeSpace(_ path: String) throws -> [String: Any] {
    let keys: Set<URLResourceKey> = [.volumeTotalCapacityKey, .volumeAvailableCapacityKey,
                                     .volumeAvailableCapacityForImportantUsageKey]
    let values = try URL(fileURLWithPath: path).resourceValues(forKeys: keys)
    guard let total = values.volumeTotalCapacity, let free = values.volumeAvailableCapacity,
          let important = values.volumeAvailableCapacityForImportantUsage
    else { throw HelperError(message: "Volume capacity unavailable") }
    return ["ok": true, "total": total, "free": free, "freeIncludingPurgeable": important]
}

func moveToTrash(_ path: String, expected: [String]) throws -> String {
    let url = URL(fileURLWithPath: path)
    guard url.resolvingSymlinksInPath().path == url.standardizedFileURL.path else {
        throw HelperError(message: "Path changed or contains a symlink")
    }
    guard try fingerprint(path) == expected else {
        throw HelperError(message: "Item changed since approval")
    }
    var result: NSURL?
    try FileManager.default.trashItem(at: url, resultingItemURL: &result)
    guard let trashPath = result?.path else {
        throw HelperError(message: "No Trash location returned")
    }
    return trashPath
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    switch (args.first, args.count) {
    case ("reveal", 2):
        try reveal(args[1])
        respond(["ok": true])
    case ("trash", 6):
        let trashPath = try moveToTrash(args[1], expected: Array(args[2...5]))
        respond(["ok": true, "trashPath": trashPath])
    case ("space", 2):
        respond(try volumeSpace(args[1]))
    case ("icon", 2), ("icon", 3):
        try exportIcon(to: args[1], symbol: args.count == 3 ? args[2] : "laptopcomputer")
        respond(["ok": true])
    default:
        throw HelperError(message: "Usage: mac-tidy-helper reveal|trash|space|icon …")
    }
} catch {
    respond(["ok": false, "error": error.localizedDescription])
    exit(1)
}
