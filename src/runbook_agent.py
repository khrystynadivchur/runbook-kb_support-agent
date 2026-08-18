import argparse
import os
import sys
import requests


def get_jira_issue(site_url: str, email: str, api_token: str, issue_key: str) -> dict:
    url = f"{site_url}/rest/api/3/issue/{issue_key}"
    params = {
        "fields": "summary,description,comment,status,project,labels,components"
    }

    response = requests.get(
        url,
        params=params,
        auth=(email, api_token),
        headers={"Accept": "application/json"},
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Cannot read Jira issue {issue_key}. "
            f"HTTP {response.status_code}: {response.text}"
        )

    return response.json()


def extract_adf_text(content) -> str:
    """
    Basic extractor for Atlassian Document Format content.
    Jira descriptions/comments are often stored in ADF JSON.
    """
    if not content:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        result = []

        if content.get("type") == "text":
            result.append(content.get("text", ""))

        for item in content.get("content", []):
            result.append(extract_adf_text(item))

        return "\n".join(filter(None, result))

    if isinstance(content, list):
        return "\n".join(extract_adf_text(item) for item in content)

    return ""


def main():
    parser = argparse.ArgumentParser(description="Runbook KB Agent")
    parser.add_argument("--issue-key", required=True, help="Example: IS-1234")
    parser.add_argument(
        "--action",
        required=True,
        choices=["create", "update"],
        help="Requested action",
    )
    parser.add_argument(
        "--dry-run",
        default="true",
        help="true = do not create/update any Confluence page",
    )
    args = parser.parse_args()

    site_url = os.getenv("ATLASSIAN_SITE_URL", "").rstrip("/")
    email = os.getenv("ATLASSIAN_EMAIL", "")
    api_token = os.getenv("ATLASSIAN_API_TOKEN", "")

    if not site_url or not email or not api_token:
        print("ERROR: Missing Atlassian configuration.", file=sys.stderr)
        print(
            "Required variables: ATLASSIAN_SITE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Starting Runbook KB Agent for: {args.issue_key}")
    print(f"Action: {args.action}")
    print(f"Dry run: {args.dry_run}")

    issue = get_jira_issue(site_url, email, api_token, args.issue_key)
    fields = issue.get("fields", {})

    summary = fields.get("summary", "To be confirmed")
    description = extract_adf_text(fields.get("description"))

    comments = fields.get("comment", {}).get("comments", [])
    comments_text = []

    for comment in comments:
        body = extract_adf_text(comment.get("body"))
        if body:
            comments_text.append(body)

    issue_url = f"{site_url}/browse/{args.issue_key}"

    print("\n=== JIRA TICKET LOADED SUCCESSFULLY ===")
    print(f"Jira ticket: {args.issue_key}")
    print(f"Jira URL: {issue_url}")
    print(f"KB title from Summary: {summary}")
    print("\n--- Description ---")
    print(description[:3000] if description else "To be confirmed.")
    print("\n--- Comments found ---")
    print(len(comments_text))

    print("\n=== NEXT STEP ===")
    print("Later the agent will search Confluence for an existing runbook.")
    print("No Confluence page was created or updated in this version.")


if __name__ == "__main__":
    main()