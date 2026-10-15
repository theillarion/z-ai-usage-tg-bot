"""Z.ai API client for checking tokens, quotas, and subscription details."""

import logging
import re
from typing import Any, Dict, Optional, Tuple
import requests


def check_token(
    token: str,
    timeout: float = 15.0,
    session: Optional[requests.Session] = None,
) -> Tuple[bool, Any]:
    """
    Validate a Z.ai token and fetch quotas and subscription info.
    Returns (True, quota_data_dict) on success, or (False, error_message_str) on failure.
    """
    http = session or requests

    url_quota = "https://api.z.ai/api/monitor/usage/quota/limit"
    url_sub_list = "https://api.z.ai/api/biz/subscription/list"
    url_sub_legacy = "https://chat.z.ai/api/v1/users/user/subscription"

    base_headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:154.0) "
            "Gecko/20100101 Firefox/154.0"
        ),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://z.ai",
        "Referer": "https://z.ai/",
        "Sec-Fetch-Mode": "cors",
    }

    headers_attempts = [
        base_headers,
        {
            **base_headers,
            "Bigmodel-Organization": "org-159Dbe6850324FBF8641C53D400Af618",
            "Bigmodel-Project": "proj_FE43189e8bf8485d85DEdeb7425FB779",
        },
    ]

    last_err = "Unknown error"
    response_data: Optional[Dict[str, Any]] = None
    successful_headers = None

    for headers in headers_attempts:
        try:
            response = http.get(url_quota, headers=headers, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    r_data = data.get("data", {})
                    response_data = r_data
                    successful_headers = headers
                    if r_data.get("limits"):
                        break
                else:
                    last_err = data.get("msg") or f"API error code {data.get('code')}"
            else:
                last_err = f"HTTP Error {response.status_code}"
        except Exception as e:
            last_err = str(e)

    if response_data is None:
        return False, last_err

    quota_data = dict(response_data)
    req_headers = successful_headers or base_headers

    # Try fetching subscription list (new Coding Plan API)
    sub_title = None
    sub_end = None
    sub_autorenew = None

    try:
        res_sub = http.get(url_sub_list, headers=req_headers, timeout=min(timeout, 5.0))
        if res_sub.status_code == 200:
            sub_json = res_sub.json()
            if sub_json.get("code") == 200:
                records = sub_json.get("data")
                if isinstance(records, list) and records:
                    active = next((s for s in records if s.get("inCurrentPeriod")), records[0])
                    prod = active.get("productName") or "GLM Coding Plan"
                    val = active.get("value") or ""
                    ver = active.get("version") or ""
                    parts = [p for p in [prod, val, f"({ver})" if ver else ""] if p]
                    sub_title = " - ".join(parts[:2]) + (f" {parts[2]}" if len(parts) > 2 else "")

                    expire = active.get("nextRenewTime")
                    if not expire and active.get("valid"):
                        matches = re.findall(
                            r"\d{4}[-/.]\d{2}[-/.]\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?",
                            str(active.get("valid")),
                        )
                        if len(matches) > 1:
                            expire = matches[-1]
                        elif len(matches) == 1:
                            expire = matches[0]
                    if not expire:
                        expire = (
                            active.get("subscriptionEndDate")
                            or active.get("expire_at")
                            or active.get("end_time")
                        )

                    sub_end = expire
                    sub_autorenew = active.get("autoRenew")
    except Exception as e:
        logging.debug(f"Subscription list error: {e}")

    # Fallback to legacy subscription endpoint if needed
    if not sub_end:
        try:
            res_sub = http.get(url_sub_legacy, headers=req_headers, timeout=min(timeout, 5.0))
            if res_sub.status_code == 200:
                sub_data = res_sub.json()
                if sub_data.get("code") == 0 and sub_data.get("data"):
                    s_data = sub_data.get("data", {})
                    sub_end = (
                        s_data.get("expire_at")
                        or s_data.get("end_time")
                        or s_data.get("current_period_end")
                    )
        except Exception:
            pass

    quota_data["plan_title"] = sub_title
    quota_data["subscription_end"] = sub_end
    quota_data["auto_renew"] = sub_autorenew
    return True, quota_data
