from collections import defaultdict
import argparse
import os
import shlex
import subprocess
import sys

__all__ = ['GitReporter', 'is_valid_git_repo']

# --- Module-level helper functions (internal) ---


def _get_git_command_output(command_str, repo_path=None):
    """
    Executes a git command and returns its standard output.

    This function is intended for internal use. It constructs and runs a git
    command, optionally targeting a specific repository path. If any error
    occurs during the execution of the command (e.g., command not found,
    non-zero exit status, or other subprocess exceptions), this function
    will silently return None.

    Args:
        command_str (str): The git command string to execute (e.g., "status", "log -1").
                           The 'git ' prefix is prepended automatically if not present.
        repo_path (str, optional): The absolute path to the git repository.
                                   If None, the command is run in the current
                                   working directory's context if it's a repo,
                                   or may fail if not in a repo.

    Returns:
        str or None: The standard output (stdout) from the executed git command
                     as a string, with leading/trailing whitespace stripped.
                     Returns None if any error occurs during command execution.
    """
    try:
        # Ensure command starts with "git"
        if command_str.lower().startswith("git "):
            base_args = shlex.split(command_str)
        else: # Prepend "git" if not present
            base_args = ['git'] + shlex.split(command_str)

        final_args = [base_args[0]]  # 'git'
        if repo_path:
            final_args.extend(['-C', repo_path])
        final_args.extend(base_args[1:])  # The rest of the command parts

        result = subprocess.run(
            final_args,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        # As requested, silently return None on any command execution error.
        return None

# --- Public Module-level function ---


def is_valid_git_repo(path_to_check):
    """
    Checks if the given path is inside a Git working tree.

    Args:
        path_to_check (str): The path to check.

    Returns:
        bool: True if it's a Git working tree, False otherwise.
    """
    # This command is specifically used for validation
    # Fixed: Comment is now outside the command string
    command = "git rev-parse --is-inside-work-tree"
    output = _get_git_command_output(
        command, repo_path=path_to_check)  # Uses internal helper
    return output == "true"


class GitReporter:
    def __init__(self, repo_path, file_line_formatter=None):
        """
        Initializes the GitReporter.

        Args:
            repo_path (str): The path to the Git repository. This path will be
                             converted to an absolute path.
            file_line_formatter (callable, optional): A function used to format
                                                      lines detailing file changes in
                                                      commit reports. If None,
                                                      `GitReporter.default_file_change_formatter`
                                                      is used.

        Raises:
            ValueError: If the `repo_path` does not point to a valid Git repository,
                        as determined by `is_valid_git_repo`.
        """
        self.repo_path = os.path.abspath(repo_path)  
        if not is_valid_git_repo(self.repo_path):
            raise ValueError(f"The path '{repo_path}' is not a valid Git repository.")
        self.file_line_formatter = file_line_formatter if file_line_formatter else GitReporter.default_file_change_formatter

    def get_latest_commit_hash(self):
        """
        Retrieves the full commit hash of the latest commit (HEAD) in the repository.

        Returns:
            str: The full hash of the latest commit, or None if it fails.
        """
        command = "git rev-parse HEAD"
        latest_hash = _get_git_command_output(command, repo_path=self.repo_path)  # Uses internal helper
        return latest_hash

    def get_project_tree_info(self):
        """
        Retrieves a directory tree listing for the repository.

        Executes the `tree` command with a depth limit of 5 and ignores
        common development/temporary directories and files like .git, .exec.sh,
        node_modules, *.pyc, and __pycache__.

        Returns:
            str: A string containing the formatted tree listing. If the `tree`
                 command fails or is not found, it returns "No tree info.\n\n".
                 The output always ends with two newline characters.
        """
        tree_info = self.execute_external_command(
            "tree",
            "-L 5",
            "-I",
            ".git", 
            ".exec.sh", 
            "node_modules", 
            "*.pyc", 
            "__pycache__",
        )
        if tree_info is None:
            return "No tree info.\n\n"
        else:
            return tree_info + "\n\n"

    @staticmethod
    def default_file_change_formatter(path, change_type, lines_added, lines_deleted):
        """
        Formats a line describing a file change for inclusion in a commit report.

        This is the default formatter used by GitReporter if no other formatter
        is provided during initialization.

        Args:
            path (str): The file path relative to the repository root.
            change_type (str): The type of change (e.g., "added", "modified", "deleted", "renamed").
            lines_added (int): The number of lines added to the file.
            lines_deleted (int): The number of lines deleted from the file.

        Returns:
            str: A formatted string representing the file change.
                 Example: "[src/main.py] [modified] +[10] -[2]"
        """
        return f"[{path}] [{change_type}] +[{lines_added}] -[{lines_deleted}]"

    def execute_external_command(self, command_name, common_args=None,
                                 pattern_arg_flag="-I", *patterns_to_process):
        """
        Executes an external command with specified arguments and pattern processing.

        Constructs and runs a command in the repository's root directory.
        The command is built by first including the `command_name`, then any
        pattern-related arguments (each pattern prefixed by `pattern_arg_flag`),
        and finally any `common_args`.

        Args:
            command_name (str): The name of the command to execute (e.g., "tree", "ls").
                                This argument is mandatory.
            common_args (str, optional): A string containing common arguments for the
                                         command (e.g., "-L 5", "-al --sort=time").
                                         These are appended after pattern arguments.
            pattern_arg_flag (str, optional): The flag used to prefix each pattern
                                              (e.g., "-I" for `tree`, "--exclude=" for `tar`).
                                              Defaults to "-I".
            *patterns_to_process (str): Variable number of pattern strings to be
                                        processed. Each pattern will be prefixed by
                                        `pattern_arg_flag`. For example, if `pattern_arg_flag`
                                        is "-I" and `patterns_to_process` are "*.pyc",
                                        "__pycache__", this will result in
                                        `-I "*.pyc" -I "__pycache__"` being added to the command.

        Returns:
            str or None: The standard output (stdout) of the executed command as a
                         string, with leading/trailing whitespace stripped. Returns
                         None if `command_name` is not provided, or if the command
                         execution fails for any reason (e.g., command not found,
                         non-zero exit status).
        """
        if not command_name:
            return None  # Command name is mandatory

        command_parts = [command_name]

        # Add pattern arguments first, as requested
        if patterns_to_process and pattern_arg_flag:
            for pattern in patterns_to_process:
                command_parts.extend([pattern_arg_flag, pattern])

        # Then add common arguments
        if common_args:
            # shlex.split handles multiple options within common_args string
            command_parts.extend(shlex.split(common_args))

        try:
            # Execute the command in the repository's directory
            result = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                check=True,  # Will raise CalledProcessError for non-zero exit codes
                encoding='utf-8',
                cwd=self.repo_path  # Run the command in the context of the repository
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            print(result.stderr)
            return None

    def execute_bash_script(
        self, 
        script_name: str):
        """
        Executes a bash script in the repository's root directory.

        Args:
            script_name (str): The name of the bash script file to execute.
                               It is expected that this script is located in the
                               repository's root directory.

        Returns:
            subprocess.CompletedProcess: An object representing the result of the
                                         script execution. This object contains
                                         attributes like `returncode`, `stdout`, and
                                         `stderr`.

        Raises:
            subprocess.CalledProcessError: If the executed script returns a non-zero
                                         exit code. The `check=True` argument to
                                         `subprocess.run` ensures this.
            FileNotFoundError: If the specified `script_name` (or `bash` itself)
                               cannot be found.
            Exception: For other potential issues during command execution, such as
                       permission errors or other `subprocess.run` failures.
        """
        try:
            result = subprocess.run(
                f"bash {script_name}",
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            return result

        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            if e.stdout:
                print("STDOUT (on error):")
                print(e.stdout.strip())
            if e.stderr:
                print("STDERR (on error):")
                print(e.stderr.strip())
            raise  # Re-raise the exception after printing details
        except FileNotFoundError:
            # This specific FileNotFoundError refers to the command itself not being found
            print(
                f"Error: Command '{command}' not found. Make sure it's in your system's PATH.")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise


    def generate_commit_report(self, commit_hash):
        """
        Generates a detailed, formatted report for a specific git commit.

        The report includes commit metadata (hash, author, date), the commit
        message, and a list of changed files with their respective lines added
        and deleted. The formatting of file change lines is handled by the
        `file_line_formatter` set during the GitReporter's initialization.

        This method fetches information using several git commands:
        - `git show --no-patch --date=default --pretty=format:'...' <hash>` for metadata.
        - `git show --no-patch --pretty="format:%B" <hash>` for the commit message.
        - `git show --numstat --pretty="format:" <hash>` for lines added/deleted per file.
        - `git show --name-status --pretty="format:" <hash>` for change types (added, modified, etc.).

        If any of these git commands fail (e.g., invalid commit hash), the
        report generation might be incomplete or return an error message.

        Args:
            commit_hash (str): The full or short hash of the commit for which
                               to generate the report.

        Returns:
            str: A string containing the formatted commit report. If fetching
                 commit metadata fails, a specific error message is returned.
                 The report is structured with metadata, commit message (indented),
                 and then a list of file changes.
        """
        output_lines = []

        # 1. Get commit metadata
        metadata_format = "commit %H%d%nAuthor: %an <%ae>%nDate:   %ad"
        metadata_command = f"git show --no-patch --date=default --pretty=format:'{metadata_format}' {commit_hash}"
        commit_metadata = _get_git_command_output(
            metadata_command, repo_path=self.repo_path)

        if commit_metadata is None:
            # The git command already failed silently, so we provide a contextual error here.
            return f"Could not generate report (failed to retrieve metadata for commit {commit_hash})."
        output_lines.append(commit_metadata)

        # 2. Get commit message body
        message_body_command = f'git show --no-patch --pretty="format:%B" {commit_hash}'
        commit_message_body_raw = _get_git_command_output(
            message_body_command, repo_path=self.repo_path)
        has_message = commit_message_body_raw is not None and commit_message_body_raw.strip()

        output_lines.append("")

        if has_message:
            indented_message_lines = [
                "    " + line for line in commit_message_body_raw.split('\n')]
            output_lines.extend(indented_message_lines)
            output_lines.append("")

        # --- File statistics ---
        files_data = defaultdict(lambda: {"la": 0, "ld": 0, "type": "unknown"})

        # 3. Get numstat
        numstat_command = f'git show --numstat --pretty="format:" {commit_hash}'
        numstat_output = _get_git_command_output(
            numstat_command, repo_path=self.repo_path)

        if numstat_output is not None:
            for line in numstat_output.split('\n'):
                if not (line := line.strip()):
                    continue
                parts = line.split('\t')
                if len(parts) == 3:
                    la_str, ld_str, path = parts
                    la = 0 if la_str == '-' else int(la_str)
                    ld = 0 if ld_str == '-' else int(ld_str)
                    files_data[path]["la"] = la
                    files_data[path]["ld"] = ld
                else:
                    # Silently skip malformed lines
                    pass

        # 4. Get name-status
        name_status_command = f'git show --name-status --pretty="format:" {commit_hash}'
        name_status_output = _get_git_command_output(
            name_status_command, repo_path=self.repo_path)

        if name_status_output is not None:
            for line in name_status_output.split('\n'):
                if not (line := line.strip()):
                    continue
                parts = line.strip().split('\t')
                status_char = parts[0][0]

                current_file_path = ""
                change_type = "unknown"

                if status_char in ('A', 'M', 'D', 'T'):
                    change_types_map = {
                        'A': 'added', 'M': 'modified', 'D': 'deleted', 'T': 'modified'}
                    change_type = change_types_map[status_char]
                    current_file_path = parts[1]
                elif status_char in ('R', 'C'):
                    change_types_map = {'R': 'renamed', 'C': 'added'}
                    change_type = change_types_map[status_char]
                    current_file_path = parts[2]
                else:
                    # Silently skip unhandled statuses
                    continue

                if current_file_path:
                    files_data[current_file_path]["type"] = change_type

        # 5. Format file change lines using the instance's formatter
        if files_data:
            for path in sorted(files_data.keys()):
                data = files_data[path]
                file_type = data["type"] if data["type"] != "unknown" else "modified"
                # Use the formatter stored in the instance
                formatted_line = self.file_line_formatter(
                    path, file_type, data['la'], data['ld'])
                output_lines.append(formatted_line)

        return "\n".join(output_lines)


def _main():  # Renamed from main
    """
    Command-line interface entry point for the GitReporter script.

    Parses command-line arguments to specify a Git repository and optional
    actions like displaying the file tree (`--tree`) or disk usage (`--du`).
    It initializes a `GitReporter` for the target repository and prints a
    report for the latest commit. If additional action flags are provided,
    it executes those commands and prints their output.

    This function is intended for direct script execution and handles argument
    parsing, error reporting to stderr, and exiting with appropriate status codes.
    """
    parser = argparse.ArgumentParser(
        description="Generate a report for the last commit in a Git repository. "
                    "Can also execute auxiliary commands like tree, du.",  # Removed tar from description
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-r", "--repository",
        help="Path to the Git repository. \nDefaults to the current working directory if not specified."
    )
    parser.add_argument(
        "-t", "--tree",
        action="store_true",
        help="Display the file tree (uses 'tree -L 3', ignores .git, node_modules, *.pyc, __pycache__)."
    )
    parser.add_argument(
        "-d", "--du",
        action="store_true",
        help="Display disk usage (uses 'du -ch', ignores .git, __pycache__)."
    )
    # Removed --tar argument
    args = parser.parse_args()

    repo_to_check = args.repository if args.repository else os.getcwd()

    reporter = None
    try:
        reporter = GitReporter(repo_to_check)
    except ValueError as e:
        print(e, file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(
            f"An unexpected error occurred during GitReporter initialization: {e}", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    latest_hash = reporter.get_latest_commit_hash()

    if latest_hash:
        report = reporter.generate_commit_report(latest_hash)
        print(report)  # Print the commit report

        if args.tree:
            print("\n" + "="*20 + " FILE TREE " + "="*20 + "\n")
            tree_output = reporter.execute_external_command(
                # command_name (positional)
                "tree",
                # common_args (positional)
                "-L 3",
                # pattern_arg_flag (positional)
                "-I",
                ".git", "node_modules", "*.pyc", "__pycache__"      # *patterns_to_process
            )
            if tree_output:
                print(tree_output)
            else:
                print(
                    "Could not generate file tree (is 'tree' command installed and accessible?).", file=sys.stderr)

        if args.du:
            print("\n" + "="*20 + " DISK USAGE (du) " + "="*20 + "\n")
            du_output = reporter.execute_external_command(
                # command_name (positional)
                "du",
                # common_args (positional)
                "-ch",
                # pattern_arg_flag (positional)
                "-I",
                ".git", "__pycache__"                              # *patterns_to_process
            )
            if du_output:
                print(du_output)
            else:
                print(
                    "Could not generate disk usage (is 'du' command installed and accessible?).", file=sys.stderr)

        # Removed --tar block

    else:
        print(
            f"Error: Could not find latest commit hash in '{reporter.repo_path}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
