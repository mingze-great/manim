import argparse
import socket
import sys
import time

import paramiko


def run_remote_command(args: argparse.Namespace) -> int:
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
        _, stdout, stderr = client.exec_command(args.command, timeout=args.timeout)
        exit_code = stdout.channel.recv_exit_status()
        sys.stdout.buffer.write(stdout.read())
        sys.stderr.buffer.write(stderr.read())
        return exit_code
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("command")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--keepalive", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=5)
    args = parser.parse_args()

    last_error = None
    for attempt in range(1, args.retries + 1):
        try:
            return run_remote_command(args)
        except (paramiko.SSHException, socket.timeout, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == args.retries:
                break
            print(
                f"remote_exec attempt {attempt}/{args.retries} failed: {exc}; retrying in {args.retry_delay}s",
                file=sys.stderr,
            )
            time.sleep(args.retry_delay)

    print(f"remote_exec failed after {args.retries} attempts: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
