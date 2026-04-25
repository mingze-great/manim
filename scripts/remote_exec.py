import argparse
import sys

import paramiko


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("command")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, username=args.user, password=args.password, timeout=20)
    try:
        stdin, stdout, stderr = client.exec_command(args.command, timeout=args.timeout)
        sys.stdout.buffer.write(stdout.read())
        sys.stderr.buffer.write(stderr.read())
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
