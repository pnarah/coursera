from lib.register_tools import prompt_expert, prompt_llm_for_json
from lib.modules import Agent, AgentFunctionCallingActionLanguage, PythonActionRegistry, generate_response, register_tool, Goal


@register_tool(tags=["invoice_processing", "categorization"])
def categorize_expenditure(action_context: ActionContext, description: str) -> str:
    """
    Categorize an invoice expenditure based on a short description.
    
    Args:
        description: A one-sentence summary of the expenditure.
        
    Returns:
        A category name from the predefined set of 20 categories.
    """
    categories = [
        "Office Supplies", "IT Equipment", "Software Licenses", "Consulting Services", 
        "Travel Expenses", "Marketing", "Training & Development", "Facilities Maintenance",
        "Utilities", "Legal Services", "Insurance", "Medical Services", "Payroll",
        "Research & Development", "Manufacturing Supplies", "Construction", "Logistics",
        "Customer Support", "Security Services", "Miscellaneous"
    ]
    
    return prompt_expert(
        action_context=action_context,
        description_of_expert="A senior financial analyst with deep expertise in corporate spending categorization.",
        prompt=f"Given the following description: '{description}', classify the expense into one of these categories:\n{categories}"
    )


# @register_tool(tags=["invoice_processing", "validation"])
# def check_purchasing_rules(action_context: ActionContext, invoice_data: dict) -> dict:
#     """
#     Validate an invoice against company purchasing policies.
    
#     Args:
#         invoice_data: Extracted invoice details, including vendor, amount, and line items.
        
#     Returns:
#         A dictionary indicating whether the invoice is compliant, with explanations.
#     """
#     # Load the latest purchasing rules from disk
#     rules_path = "config/purchasing_rules.txt"
    
#     try:
#         with open(rules_path, "r") as f:
#             purchasing_rules = f.read()
#     except FileNotFoundError:
#         purchasing_rules = "No rules available. Assume all invoices are compliant."

#     return prompt_expert(
#         action_context=action_context,
#         description_of_expert="A corporate procurement compliance officer with extensive knowledge of purchasing policies.",
#         prompt=f"""
#         Given this invoice data: {invoice_data}, check whether it complies with company purchasing rules.
#         The latest purchasing rules are as follows:
        
#         {purchasing_rules}
        
#         Identify any violations or missing requirements. Respond with:
#         - "compliant": true or false
#         - "issues": A brief explanation of any problems found
#         """
#     )

@register_tool(tags=["invoice_processing", "validation"])
def check_purchasing_rules(action_context: ActionContext, invoice_data: dict) -> dict:
    """
    Validate an invoice against company purchasing policies, returning a structured response.
    
    Args:
        invoice_data: Extracted invoice details, including vendor, amount, and line items.
        
    Returns:
        A structured JSON response indicating whether the invoice is compliant and why.
    """
    rules_path = "config/purchasing_rules.txt"

    try:
        with open(rules_path, "r") as f:
            purchasing_rules = f.read()
    except FileNotFoundError:
        purchasing_rules = "No rules available. Assume all invoices are compliant."

    validation_schema = {
        "type": "object",
        "properties": {
            "compliant": {"type": "boolean"},
            "issues": {"type": "string"}
        }
    }

    return prompt_llm_for_json(
        action_context=action_context,
        schema=validation_schema,
        prompt=f"""
        Given this invoice data: {invoice_data}, check whether it complies with company purchasing rules.
        The latest purchasing rules are as follows:
        
        {purchasing_rules}
        
        Respond with a JSON object containing:
        - `compliant`: true if the invoice follows all policies, false otherwise.
        - `issues`: A brief explanation of any violations or missing requirements.
        """
    )


def create_invoice_agent():
    # Create action registry with invoice tools
    action_registry = PythonActionRegistry()

    # Define invoice processing goals
    goals = [
        Goal(
            name="Persona",
            description="You are an Invoice Processing Agent, specialized in handling invoices efficiently."
        ),
        Goal(
            name="Process Invoices",
            description="""
            Your goal is to process invoices accurately. For each invoice:
            1. Extract key details such as vendor, amount, and line items.
            2. Generate a one-sentence summary of the expenditure.
            3. Categorize the expenditure using an expert.
            4. Validate the invoice against purchasing policies.
            5. Store the processed invoice with categorization and validation status.
            6. Return a summary of the invoice processing results.
            """
        )
    ]

    # Define agent environment
    environment = PythonEnvironment()

    return Agent(
        goals=goals,
        agent_language=AgentFunctionCallingActionLanguage(),
        action_registry=action_registry,
        generate_response=generate_response,
        environment=environment
    )

# Step 4: Testing the New Capabilities
invoice_text = """
    Invoice #4567
    Date: 2025-02-01
    Vendor: Tech Solutions Inc.
    Items: 
      - Laptop - $1,200
      - External Monitor - $300
    Total: $1,500
"""

# Create an agent instance
agent = create_invoice_agent()

# Process the invoice
response = agent.run(f"Process this invoice:\n\n{invoice_text}")

print(response)