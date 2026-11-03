"""Developer clutter: tool caches with their official cleanup command, and
project dependencies (node_modules) with their age."""

from dataclasses import asdict, dataclass
from pathlib import Path
from ..common.paths import personal_path

STALE_DAYS = 90


@dataclass(frozen=True)
class Tool:
    name: str
    path: str  # relative to home
    advice: str
    command: str = ""


TOOLS = (
    Tool("Xcode DerivedData", "Library/Developer/Xcode/DerivedData",
         "Build products and indexes. Xcode rebuilds them; the next build is slower.",
         ""),
    Tool("Xcode Archives", "Library/Developer/Xcode/Archives",
         "Release builds and their debug symbols. Keep archives you may need to symbolicate crash reports."),
    Tool("iOS device support", "Library/Developer/Xcode/iOS DeviceSupport",
         "Debug symbols copied from each iOS version you connected. Review old versions in Xcode; support files may need to be downloaded again.",),
    Tool("Simulators", "Library/Developer/CoreSimulator/Devices",
         "Simulator devices and their data. Remove ones for runtimes you no longer have.",
         "xcrun simctl delete unavailable"),
    Tool("Docker", "Library/Containers/com.docker.docker",
         "Docker’s virtual disk and app data. Image limits differ from allocated storage; review images, containers and volumes in Docker.",
         "docker system df"),
    Tool("npm cache", ".npm", "Downloaded packages, temporary npx installs and logs. Inspect before clearing.", "npm cache clean --force"),
    Tool("Yarn cache", "Library/Caches/Yarn", "Downloaded packages.", "yarn cache clean"),
    Tool("pnpm store", "Library/pnpm/store", "Content-addressed package store.", "pnpm store prune"),
    Tool("pnpm cache", "Library/Caches/pnpm", "Package metadata cache.", "pnpm store prune"),
    Tool("pip cache", "Library/Caches/pip", "Downloaded Python wheels.", "pip cache purge"),
    Tool("uv cache", ".cache/uv", "Python packages cached by uv.", "uv cache clean"),
    Tool("Conda packages", "miniconda3/pkgs", "Downloaded Conda packages.", "conda clean --all"),
    Tool("Conda packages", "anaconda3/pkgs", "Downloaded Conda packages.", "conda clean --all"),
    Tool("Homebrew downloads", "Library/Caches/Homebrew", "Old bottles and source downloads.", "brew cleanup -n"),
    Tool("Gradle caches", ".gradle/caches", "Android and JVM build caches.", ""),
    Tool("Maven repository", ".m2/repository", "Downloaded JVM dependencies. Re-downloaded on the next build."),
    Tool("Cargo registry", ".cargo/registry", "Downloaded Rust crates.", ""),
    Tool("Rust toolchains", ".rustup/toolchains", "Installed Rust compilers.", "rustup toolchain list"),
    Tool("CocoaPods cache", "Library/Caches/CocoaPods", "Downloaded pods.", "pod cache clean --all"),
    Tool("Android SDK", "Library/Android/sdk", "System images and platforms. Remove unused ones in Android Studio's SDK Manager."),
    Tool("Ollama models", ".ollama/models", "Local AI models. Each can be several GB.", "ollama list && ollama rm <model>"),
    Tool("Hugging Face cache", ".cache/huggingface", "Downloaded models and datasets.", "huggingface-cli delete-cache"),
)


def _has_ancestor_named(d, dirs, name):
    parent = d["parent"]
    while parent is not None:
        if dirs[parent]["name"] == name:
            return True
        parent = dirs[parent]["parent"]
    return False


def _row_summary(d):
    return {key: d[key] for key in ("id", "path", "size", "partial", "mtime", "trashPolicy")}


def developer_summary(report, now):
    home = report["home"]
    dirs = report["dirs"]
    by_path = {d["path"]: d for d in dirs}

    tools = []
    for tool in TOOLS:
        row = by_path.get(f"{home}/{tool.path}")
        if row and row["size"] > 0:
            tools.append({**asdict(tool), **_row_summary(row)})

    projects = []
    for d in dirs:
        if d["name"] == "node_modules" and personal_path(str(Path(d["path"]).parent),home) and not _has_ancestor_named(d, dirs, "node_modules"):
            project = dirs[d["parent"]] if d["parent"] is not None else None
            latest = max(d.get("latestMtime",d["mtime"]), project.get("latestMtime",project["mtime"]) if project else d["mtime"])
            age_days = max(0,int((now - latest) // 86400))
            projects.append({
                **_row_summary(d),
                "project": project["name"] if project else d["path"],
                "projectPath": project["path"] if project else d["path"],
                "ageDays": age_days,
                "stale": age_days >= STALE_DAYS and not d.get("partial") and not (project and project.get("partial")),
            })

    tools.sort(key=lambda t: t["size"], reverse=True)
    projects.sort(key=lambda p: p["size"], reverse=True)
    return {
        "tools": tools,
        "projects": projects,
        "projectBytes": sum(p["size"] for p in projects),
        "staleBytes": sum(p["size"] for p in projects if p["stale"]),
        "staleDays": STALE_DAYS,
        "ageBasis": "latest observed modification in the project; not last opened",
    }
