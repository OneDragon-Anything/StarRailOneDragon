import os
import re
import subprocess


def main() -> int:
    github_ref = os.environ.get('GITHUB_REF', '')
    github_output = os.environ.get('GITHUB_OUTPUT')
    create_release = os.environ.get('CREATE_RELEASE', 'false').lower() == 'true'

    version = ""
    should_push_tag = False

    if github_ref.startswith('refs/tags/'):
        # 已由 tag 推送触发，直接使用该 tag 作为版本
        version = github_ref[10:]
    elif create_release:
        # 手动触发且要求创建 release：生成新的 beta 版本
        # 获取远程 tag 列表，由脚本显式解析稳定版与 beta 版本顺序
        cmd = ['git', 'ls-remote', '--refs', '--tags', 'origin', 'v*']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
            raise RuntimeError(f"git ls-remote failed ({result.returncode}): {detail}")

        version_tags: list[tuple[tuple[int, int, int, int, int], str, int | None]] = []
        for line in result.stdout.splitlines():
            match = re.search(r'refs/tags/(v(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?)$', line)
            if not match:
                continue
            beta_number = int(match.group(5)) if match.group(5) is not None else None
            sort_key = (
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                1 if beta_number is None else 0,
                beta_number or 0,
            )
            version_tags.append((sort_key, match.group(1), beta_number))

        if not version_tags:
            # 仓库还没有任何符合语义版本的 tag，初始化
            version = "v0.1.0-beta.1"
        else:
            latest_key, latest_tag, latest_beta = max(version_tags, key=lambda item: item[0])
            print(f"Latest tag: {latest_tag}")
            major, minor, patch = latest_key[:3]
            if latest_beta is not None:
                version = f"v{major}.{minor}.{patch}-beta.{latest_beta + 1}"
            else:
                version = f"v{major}.{minor}.{patch + 1}-beta.1"

        should_push_tag = True
    else:
        # PR 或非发布构建
        short_hash = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True,
        ).stdout.strip() or 'unknown'

        pr_match = re.match(r'^refs/pull/(\d+)/', github_ref)
        if pr_match:
            version = f"pr{pr_match.group(1)}+{short_hash}"
        else:
            version = f"dev+{short_hash}"

    print(f"Version: {version}")

    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"version={version}\n")

    if should_push_tag:
        print(f"Creating and pushing new tag: {version}")
        subprocess.run(['git', '-c', 'user.name=GitHub Actions', '-c', 'user.email=actions@github.com', 'tag', version], check=True)
        subprocess.run(['git', 'push', 'origin', version], check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
