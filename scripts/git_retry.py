import argparse
import subprocess
import sys
import time


TRANSIENT_PATTERNS = (
    "connection was reset",
    "connection reset",
    "could not connect to server",
    "empty reply from server",
    "failed to connect",
    "gnutls recv error",
    "non-properly terminated",
    "operation timed out",
    "timed out",
    "recv failure",
    "http/2 stream",
    "remote end hung up unexpectedly",
    "unexpected eof",
    "early eof",
    "connection died",
)


def is_transient_failure(output: str) -> bool:
    lowered = output.lower()
    return any(pattern in lowered for pattern in TRANSIENT_PATTERNS)


def build_command(args: argparse.Namespace) -> list[str]:
    command = ["git"]
    if args.github_https_workaround:
        command.extend([
            "-c",
            "http.version=HTTP/1.1",
            "-c",
            "http.maxRequests=1",
        ])
    command.extend(args.git_args)
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run git with retry/backoff for transient GitHub HTTPS failures."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--github-https-workaround", action="store_true", default=True)
    parser.add_argument("git_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.git_args:
        parser.error("missing git arguments")

    if args.git_args[0] == "--":
        args.git_args = args.git_args[1:]

    command = build_command(args)
    last_result = None
    for attempt in range(1, args.retries + 1):
        result = subprocess.run(command, cwd=args.repo, capture_output=True)
        last_result = result
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        if result.returncode == 0:
            return 0

        combined_output = b"\n".join([result.stdout, result.stderr]).decode("utf-8", errors="replace")
        if attempt == args.retries or not is_transient_failure(combined_output):
            return result.returncode

        print(
            f"git_retry attempt {attempt}/{args.retries} hit transient transport failure; retrying in {args.retry_delay}s",
            file=sys.stderr,
        )
        time.sleep(args.retry_delay)

    return 1 if last_result is None else last_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
