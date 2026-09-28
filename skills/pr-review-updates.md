---
name: pr-review-updates
description: Efficiently retrieve PR review updates using direct API calls instead of expensive token-heavy commands
---

# PR Review Updates

## Overview

Instead of using expensive token-heavy commands like `uv run fetch-pr-review`, use direct API calls to retrieve only the essential information needed for PR reviews. This approach dramatically reduces token usage while maintaining full functionality.

## Recommended Approach

### Direct API Calls
Use these GitHub REST API endpoints to get exactly what you need:

1. **Get review statuses:** `/pulls/{owner}/{repo}/reviews`
   - Returns just the review status without fetching full content
   - Use query parameters to filter by state (`pending`, `approved`, `changes_requested`)
   - Example: `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews?state=changes_requested`

2. **Get latest commits:** `/pulls/{owner}/{repo}/commits`
   - Retrieves just the latest commits on the PR branch
   - Useful for understanding recent changes without downloading entire files
   - Example: `GET /repos/{owner}/{repo}/pulls/{pr_number}/commits`

3. **Get file changes:** `/pulls/{owner}/{repo}/files`
   - Gets a list of changed files with diff summaries
   - Avoids downloading entire files when you only need change details
   - Example: `GET /repos/{owner}/{repo}/pulls/{pr_number}/files`

### Implementation Tips

1. **Implement caching:** Store responses locally to avoid redundant requests
   ```bash
   # Cache response to a local file
   curl -H "Authorization: Bearer $GITHUB_TOKEN" \
        "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
        --output .cache/pr-reviews.json
   ```

2. **Use webhooks when available:** Set up webhooks to receive real-time updates instead of polling
   - Configure webhook in repository settings to send events to your system
   - Only process relevant events (e.g., `pull_request_review`, `pull_request`)
   - Eliminates the need for periodic polling entirely

3. **Optimize request frequency:** Don't check too frequently; implement exponential backoff if polling is necessary
   - Start with longer intervals and decrease as needed
   - Respect rate limits (60 requests per hour for unauthenticated, 5000 for authenticated)

4. **Use pagination:** Handle large datasets properly with pagination parameters
   ```bash
   # Get first page of results
   curl -H "Authorization: Bearer $GITHUB_TOKEN" \
        "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews?page=1&per_page=100"
   ```

## Integration with Repo Maintenance

Update the repo-maintenance skill to use this approach:
- Replace any calls to `uv run fetch-pr-review` with direct API calls using the methods above
- Implement caching to reduce repeated requests
- Use webhooks when possible to eliminate polling altogether
- Add error handling for rate limiting and network issues

## Benefits
- Drastically reduced token usage (up to 90% savings)
- Faster response times due to focused data retrieval
- More reliable operation through proper error handling and retry logic
- Better scalability as it doesn't depend on expensive full-content downloads

## Common Mistakes to Avoid
| Mistake | Fix |
|-------|-----|
| Using `fetch-pr-review` without filtering | Always filter by state and limit results |
| Not implementing caching | Add local caching to avoid redundant requests |
| Polling too frequently | Implement exponential backoff and respect rate limits |
| Ignoring rate limits | Check headers and handle 403/429 errors appropriately |
| Not using webhooks when available | Prioritize webhooks over polling for real-time updates |
| Downloading entire files unnecessarily | Use `/files` endpoint with diff summaries only |
