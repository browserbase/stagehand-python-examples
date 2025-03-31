import logging
import os
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
import json
from dotenv import load_dotenv

from stagehand.sync import Stagehand, StagehandConfig
from stagehand import configure_logging

# Create a custom theme for consistent styling
custom_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "highlight": "magenta",
        "url": "blue underline",
    }
)

# Create a Rich console instance with our theme
console = Console(theme=custom_theme)

load_dotenv()

# Configure logging with the utility function
configure_logging(
    level=logging.DEBUG,  # Set to DEBUG to see all logs, including verbosity level 3
)

# Set higher log levels for noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
# Set stagehand.utils to WARNING level
logging.getLogger("stagehand.utils").setLevel(logging.WARNING)

console.print(
    Panel.fit(
        "[yellow]Logging Levels:[/]\n"
        "[white]- Set [bold]verbose=1[/] for minimal logs (INFO)[/]\n"
        "[white]- Set [bold]verbose=2[/] for medium logs (WARNING)[/]\n"
        "[white]- Set [bold]verbose=3[/] for detailed logs (DEBUG)[/]",
        title="Verbosity Options",
        border_style="blue",
    )
)

def main():
    # Build a unified configuration object for Stagehand
    config = StagehandConfig(
        env="BROWSERBASE",
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        headless=False,
        dom_settle_timeout_ms=3000,
        model_name="gpt-4o",
        self_heal=True,
        wait_for_captcha_solves=True,
        act_timeout_ms=60000,  # 60 seconds timeout for actions
        system_prompt="You are a browser automation assistant that helps users navigate websites effectively.",
        model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
    )

    # Create a Stagehand client using the configuration object.
    # Change verbose level (1-3) to control log verbosity:
    # 1 = minimal logs, 2 = medium logs, 3 = detailed logs
    stagehand = Stagehand(
        config=config, server_url=os.getenv("STAGEHAND_SERVER_URL"), verbose=3
    )

    # Initialize - this creates a new session automatically.
    console.print("\n🚀 [info]Initializing Stagehand...[/]")
    stagehand.init()
    console.print(f"\n[yellow]Created new session:[/] {stagehand.session_id}")
    console.print(
        f"🌐 [white]View your live browser:[/] [url]https://www.browserbase.com/sessions/{stagehand.session_id}[/]"
    )

    import time

    time.sleep(2)

    console.print("\n▶️ [highlight] Navigating[/] to Google")
    stagehand.page.goto("https://google.com/")
    console.print("✅ [success]Navigated to Google[/]")

    console.print("\n▶️ [highlight] Clicking[/] on About link")
    # Click on the "About" link using Playwright
    stagehand.page.get_by_role("link", name="About", exact=True).click()
    console.print("✅ [success]Clicked on About link[/]")

    time.sleep(2)
    console.print("\n▶️ [highlight] Navigating[/] back to Google")
    stagehand.page.goto("https://google.com/")
    console.print("✅ [success]Navigated back to Google[/]")

    console.print("\n▶️ [highlight] Performing action:[/] search for openai")
    stagehand.page.act("search for openai")
    stagehand.page.keyboard.press("Enter")
    console.print("✅ [success]Performing Action:[/] Action completed successfully")

    console.print("\n▶️ [highlight] Observing page[/] for news button")
    observed = stagehand.page.observe("find the news button on the page")
    if len(observed) > 0:
        element = observed[0]
        console.print("✅ [success]Found element:[/] News button")
        stagehand.page.act(element)
    else:
        console.print("❌ [error]No element found[/]")

    console.print("\n▶️ [highlight] Extracting[/] first search result")
    data = stagehand.page.extract("extract the first result from the search")
    console.print("📊 [info]Extracted data:[/]")
    console.print_json(f"{data.model_dump_json()}")

    # Close the session
    console.print("\n⏹️ [warning]Closing session...[/]")
    stagehand.close()
    console.print("✅ [success]Session closed successfully![/]")
    console.rule("[bold]End of Example[/]")


if __name__ == "__main__":
    # Add a fancy header
    console.print(
        "\n",
        Panel.fit(
            "[light_gray]Stagehand 🤘 Python Sync Example[/]",
            border_style="green",
            padding=(1, 10),
        ),
    )
    main()
