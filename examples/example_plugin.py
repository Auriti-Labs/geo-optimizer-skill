"""
Example GEO Optimizer plugin — Custom audit check.

This plugin demonstrates how to extend GEO Optimizer with custom checks
using the CheckRegistry entry_points system.

Installation:
    1. Create a Python package with this check class
    2. Register it in your pyproject.toml:

        [project.entry-points."geo_optimizer.checks"]
        word_count_check = "my_package:WordCountCheck"

    3. Install your package: pip install my-package
    4. Run audit: geo audit --url https://example.com
       (your check runs automatically)

The check result appears in AuditResult.extra_checks (does not affect base score).
"""

from geo_optimizer.core.registry import CheckResult


class WordCountCheck:
    """Check that verifies minimum content length for AI visibility.

    Sites with fewer than 500 words on the homepage tend to get
    lower AI search visibility (less content to cite).
    """

    name = "word_count_minimum"
    description = "Verifies homepage has enough content for AI citation (>500 words)"
    max_score = 10

    def run(self, url: str, soup=None, **kwargs) -> CheckResult:
        """Run the word count check.

        Args:
            url: URL being audited.
            soup: BeautifulSoup of the homepage HTML.

        Returns:
            CheckResult with score based on word count thresholds.
        """
        if soup is None:
            return CheckResult(
                name=self.name,
                score=0,
                max_score=self.max_score,
                passed=False,
                message="No HTML content available",
            )

        # Remove script/style tags before counting
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())

        if word_count >= 1000:
            score = 10
            message = f"Excellent content length: {word_count} words"
        elif word_count >= 500:
            score = 7
            message = f"Good content length: {word_count} words"
        elif word_count >= 200:
            score = 4
            message = f"Minimal content: {word_count} words (aim for 500+)"
        else:
            score = 1
            message = f"Very short content: {word_count} words (aim for 500+)"

        return CheckResult(
            name=self.name,
            score=score,
            max_score=self.max_score,
            passed=word_count >= 500,
            message=message,
            details={"word_count": word_count},
        )


# ─── Quick test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from bs4 import BeautifulSoup

    html = "<html><body><p>" + "Hello world. " * 100 + "</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")

    check = WordCountCheck()
    result = check.run("https://example.com", soup=soup)
    print(f"Score: {result.score}/{result.max_score}")
    print(f"Passed: {result.passed}")
    print(f"Message: {result.message}")
