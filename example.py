import asyncio
import logging
import os
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from pydantic import BaseModel, Field, HttpUrl
from dotenv import load_dotenv
import time

from stagehand import StagehandConfig, Stagehand, configure_logging
from stagehand.schemas import ObserveOptions, ActOptions, ExtractOptions
from stagehand.a11y.utils import get_accessibility_tree, get_xpath_by_resolved_object_id

# Load environment variables
load_dotenv()

configure_logging(
    level=logging.INFO,
    remove_logger_name=True,  # Remove the redundant stagehand.client prefix
    quiet_dependencies=True,   # Suppress httpx and other noisy logs
)

# Configure Rich console
console = Console(theme=Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "highlight": "magenta",
    "url": "blue underline",
}))

# Define Pydantic models for testing
class Company(BaseModel):
    name: str = Field(..., description="The name of the company")
    url: HttpUrl = Field(..., description="The URL of the company website or relevant page")
    
class Companies(BaseModel):
    companies: list[Company] = Field(..., description="List of companies extracted from the page, maximum of 5 companies")

class ElementAction(BaseModel):
    action: str
    id: int
    arguments: list[str]

async def main():
    
    # Create configuration
    config = StagehandConfig(
        env="BROWSERBASE",
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        model_name="gemini/gemini-2.5-flash-preview-04-17",
        model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
        verbose=3,
    )
    
    # Initialize async client
    stagehand = Stagehand(
        config=config,
        env="LOCAL",
        server_url=os.getenv("STAGEHAND_SERVER_URL"),
    )
    
    try:
        # Initialize the client
        await stagehand.init()
        console.print("[success]✓ Successfully initialized Stagehand async client[/]")
        
        # Navigate to AIgrant (as in the original test)
        await stagehand.page.goto("https://www.aigrant.com")
        console.print("[success]✓ Navigated to AIgrant[/]")
        await asyncio.sleep(2)
        
        # Click the "Get Started" button
        await stagehand.page.act("click the button with text 'Get Started'")
        console.print("[success]✓ Clicked 'Get Started' button[/]")
        
        # Observe the button
        await stagehand.page.observe("the button with text 'Get Started'")
        console.print("[success]✓ Observed 'Get Started' button[/]")
        
        # Extract companies using schema
        extract_options = ExtractOptions(
            instruction="Extract the names and URLs of up to 5 companies mentioned on this page",
            schema_definition=Companies
        )
        
        extract_result = await stagehand.page.extract(extract_options)
        console.print("[success]✓ Extracted companies data[/]")
        
        # Display results
        print("Extract result:", extract_result)
        print("\nExtracted Companies:")
        if hasattr(extract_result, "companies"):
            for idx, company in enumerate(extract_result.companies, 1):
                print(f"{idx}. {company.name}: {company.url}")
        else:
            print("No companies were found in the extraction result")
        
        # XPath click
        await stagehand.page.locator("xpath=/html/body/div/ul[2]/li[2]/a").click()
        await stagehand.page.wait_for_load_state('networkidle')
        console.print("[success]✓ Clicked element using XPath[/]")
        
        # Open a new page with Google
        console.print("\n[info]Creating a new page...[/]")
        new_page = await stagehand.context.new_page()
        await new_page.goto("https://www.google.com")
        console.print("[success]✓ Opened Google in a new page[/]")
        
        # Get accessibility tree for the new page
        tree = await get_accessibility_tree(new_page, stagehand.logger)
        console.print("[success]✓ Extracted accessibility tree for new page[/]")
        
        # Try clicking Get Started button on Google
        await new_page.act("click the button with text 'Get Started'")
        
        # Use LLM to analyze the page
        response = stagehand.llm.create_response(
            messages=[
                {
                    "role": "system",
                    "content": "Based on the provided accessibility tree of the page, find the element and the action the user is expecting to perform. The tree consists of an enhanced a11y tree from a website with unique identifiers prepended to each element's role, and name. The actions you can take are playwright compatible locator actions."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"fill the search bar with the text 'Hello'\nPage Tree:\n{tree.get('simplified')}"
                        }
                    ]
                }
            ],
            model="gemini/gemini-2.5-flash-preview-04-17",
            response_format=ElementAction,
        )
        
        action = ElementAction.model_validate_json(response.choices[0].message.content)
        console.print(f"[success]✓ LLM identified element ID: {action.id}[/]")
        
        # Test CDP functionality
        args = {"backendNodeId": action.id}
        result = await new_page.send_cdp("DOM.resolveNode", args)
        object_info = result.get("object")
        print(object_info)
        
        xpath = await get_xpath_by_resolved_object_id(await new_page.get_cdp_client(), object_info["objectId"])
        console.print(f"[success]✓ Retrieved XPath: {xpath}[/]")
        
        # Interact with the element
        if xpath:
            await new_page.locator(f"xpath={xpath}").click()
            await new_page.locator(f"xpath={xpath}").fill(action.arguments[0])
            console.print("[success]✓ Filled search bar with 'Hello'[/]")
        else:
            print("No xpath found")
        
        # Final test summary
        console.print("\n[success]All async tests completed successfully![/]")
        
    except Exception as e:
        console.print(f"[error]Error during testing: {str(e)}[/]")
        raise
    finally:
        # Close the client
        # wait for 5 seconds
        await asyncio.sleep(5)
        await stagehand.close()
        console.print("[info]Stagehand async client closed[/]")

if __name__ == "__main__":
    # Add a fancy header
    console.print(
        "\n",
        Panel.fit(
            "[light_gray]Stagehand 🤘 Python Example[/]",
            border_style="green",
            padding=(1, 10),
        ),
    )
    asyncio.run(main())
