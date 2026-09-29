import asyncio
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("fixpilot.repo_reader")


class GitHubRepoReader:
    """Clones and extracts target source code files from GitHub repositories."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def fetch_target_code(
        self,
        github_url: str,
        traceback_text: str = "",
        specified_file_path: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
        """Clones repository shallowly and locates target file and ancillary context.
        
        Returns:
            (target_filename, primary_code, context_files_map)
        """
        if not github_url.startswith("http://") and not github_url.startswith("https://"):
            return None, None, {}

        temp_dir = tempfile.mkdtemp(prefix="fixpilot_repo_")
        try:
            # 1. Clone shallowly
            clone_cmd = f"git clone --depth 1 {github_url} {temp_dir}"
            proc = await asyncio.create_subprocess_shell(
                clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=self.timeout)

            if proc.returncode != 0:
                logger.warning(f"Git clone failed for {github_url}")
                return None, None, {}

            repo_path = Path(temp_dir)
            target_path = None

            # 2. Check explicitly specified path
            if specified_file_path:
                candidate = repo_path / specified_file_path
                if candidate.exists() and candidate.is_file():
                    target_path = candidate

            # 3. Detect from traceback if not specified
            if not target_path and traceback_text:
                matches = re.findall(r'File "([^"]+\.py)"', traceback_text)
                for m in reversed(matches):
                    # Check relative path or file name
                    basename = Path(m).name
                    found = list(repo_path.glob(f"**/{basename}"))
                    if found:
                        target_path = found[0]
                        break

            # 4. Fallback to main.py / app.py if still not found
            if not target_path:
                for default_name in ["main.py", "app.py", "solution.py", "index.py"]:
                    candidate = repo_path / default_name
                    if candidate.exists():
                        target_path = candidate
                        break

            if not target_path:
                # Grab first Python file found
                py_files = [f for f in repo_path.glob("**/*.py") if ".git" not in str(f)]
                if py_files:
                    target_path = py_files[0]

            if not target_path or not target_path.exists():
                return None, None, {}

            primary_code = target_path.read_text(encoding="utf-8", errors="replace")
            relative_name = str(target_path.relative_to(repo_path))

            # Gather up to 3 ancillary files as context
            context_files = {}
            for other_file in repo_path.glob("**/*.py"):
                if other_file != target_path and ".git" not in str(other_file):
                    rel = str(other_file.relative_to(repo_path))
                    context_files[rel] = other_file.read_text(encoding="utf-8", errors="replace")[:2000]
                    if len(context_files) >= 3:
                        break

            return relative_name, primary_code, context_files

        except Exception as exc:
            logger.warning(f"Error fetching repo {github_url}: {exc}")
            return None, None, {}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
