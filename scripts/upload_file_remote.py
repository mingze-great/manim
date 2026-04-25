import argparse

import paramiko


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("local_path")
    parser.add_argument("remote_path")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, username=args.user, password=args.password, timeout=20)
    try:
        sftp = client.open_sftp()
        try:
            sftp.put(args.local_path, args.remote_path)
        finally:
            sftp.close()
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
