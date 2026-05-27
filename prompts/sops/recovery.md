# Recovery SOP fragments — loaded by failure_type via prompt_loader

## TIMEOUT
1. Extend wait timeout by 2x (max 60s).
2. Simplify DOM context before retry.
3. If still failing, replan with reduced scope.

## ELEMENT_NOT_FOUND
1. Retry with role+name locator.
2. Scroll target into view.
3. Relax selector specificity.
4. Replan if all strategies exhausted.

## ACTION_NO_EFFECT
1. Click parent container.
2. Press Enter key on focused element.
3. Wait for network idle then re-verify.

## WRONG_PAGE
1. Navigate back or to start_url.
2. Replan navigation path.

## CAPTCHA_OR_LOGIN
- Do NOT attempt bypass.
- Report status as blocked and stop.
