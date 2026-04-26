import argparse
import posixpath
import socket
import sys
import time

import paramiko


def ensure_remote_parent_dir(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    parent = posixpath.dirname(remote_path)
    if not parent or parent == "/":
        return

    parts = [part for part in parent.split("/") if part]
    current = "/" if parent.startswith("/") else ""
    for part in parts:
        current = posixpath.join(current, part) if current else part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def upload_file(args: argparse.Namespace) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        timeout=args.connect_timeout,
        banner_timeout=args.connect_timeout,
        auth_timeout=args.connect_timeout,
    )
    transport = client.get_transport()
    if transport is not None:
        transport.set_keepalive(args.keepalive)

    try:
        sftp = client.open_sftp()
        try:
            if args.mkdirs:
                ensure_remote_parent_dir(sftp, args.remote_path)
            sftp.put(args.local_path, args.remote_path)
        finally:
            sftp.close()
    finally:
        client.close()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("local_path")
    parser.add_argument("remote_path")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--keepalive", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--mkdirs", action="store_true")
    args = parser.parse_args()

    last_error = None
    for attempt in range(1, args.retries + 1):
        try:
            return upload_file(args)
        except (paramiko.SSHException, socket.timeout, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == args.retries:
                break
            print(
                f"upload_file_remote attempt {attempt}/{args.retries} failed: {exc}; retrying in {args.retry_delay}s",
                file=sys.stderr,
            )
            time.sleep(args.retry_delay)

    print(f"upload_file_remote failed after {args.retries} attempts: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
