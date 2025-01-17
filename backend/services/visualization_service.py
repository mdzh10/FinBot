import os
import requests
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from sqlalchemy import text
from utils.utils import generate_database_schema, extract_sql_code, extract_python_code
from config.config import settings
from config.db.database import engine

# prompt = "generate a bar plot comparing total debit and credit for the month of November 2024 for user 1"
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o"
if settings is not None and settings.GPT4_API_KEY is not None:
    GPT4_API_KEY = settings.GPT4_API_KEY
else:
    GPT4_API_KEY = os.getenv("GPT4_API_KEY")


async def generate_visualization(prompt: str, showPopup: bool):
    # Dynamically generate the database schema
    DATABASE_SCHEMA = generate_database_schema()
    # print(DATABASE_SCHEMA)
    # Step 1: Generate SQL code to fetch the data
    sql_query = await generate_sql_code(prompt, DATABASE_SCHEMA)
    # print(sql_query)

    if not sql_query:
        return {
            "isSuccess": False,
            "msg": "Failed to generate SQL query for data extraction",
            "chart": None,
        }

    # Step 2: Execute SQL query to fetch data
    data = execute_sql_query(sql_query)
    # print(data)

    if data is None:
        return {
            "isSuccess": False,
            "msg": "Failed to fetch data with generated SQL query",
            "chart": None,
        }

    # Step 3: Generate Python code to create the plot with fetched data
    python_code = await generate_plot_code(prompt, data)
    python_code = extract_python_code(python_code)
    # print(python_code)

    if not python_code:
        return {
            "isSuccess": False,
            "msg": "Failed to generate Python code for visualization",
            "chart": None,
        }

    # Step 4: Execute the generated Python code to create the chart
    chart_image = execute_generated_code(python_code, showPopup)
    if showPopup:
        return {
            "isSuccess": True,
            "msg": "Visualization was displayed successfully.",
            "chart": None,
        }
    if not chart_image:
        return {
            "isSuccess": False,
            "msg": "Chart generation failed.",
            "chart": None,
        }

    # Successful response
    return {
        "isSuccess": True,
        "msg": "Visualization was created successfully.",
        "chart": chart_image,
    }


async def generate_sql_code(prompt: str, DATABASE_SCHEMA):
    # Combine the prompt with the database schema
    sql_prompt = (
        f"{prompt}\n\n"
        f"Generate a SQL query based on the following database schema:\n{DATABASE_SCHEMA}"
    )

    # Send request to ChatGPT to generate SQL
    headers = {
        "Authorization": f"Bearer {GPT4_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Generate SQL code based on a specific database schema. No explanation needed; just SQL code is sufficient as it would be directly executed to generate data",
            },
            {"role": "user", "content": sql_prompt},
        ],
        "temperature": 0.0,
    }

    response = requests.post(CHATGPT_API_URL, headers=headers, json=data)
    result = response.json()

    sql_code = result["choices"][0]["message"]["content"]
    return sql_code


def execute_sql_query(sql_query):
    with engine.connect() as con:
        """
        Extracts SQL code from the API response and executes it using SQLAlchemy.
        """
        try:
            # Extract the SQL code
            sql_code = extract_sql_code(sql_query)
            # print(sql_code)
            # Execute the extracted SQL
            result = con.execute(text(sql_code))
            rows = result.fetchall()
            # print(rows)
            # Retrieve column names
            columns = result.keys()
            # Convert rows to dictionaries using column names
            data = [dict(zip(columns, row)) for row in rows]
            return data
        except Exception as e:
            print(f"Error executing SQL query: {e}")
            return None


async def generate_plot_code(prompt: str, data):
    # Prepare the prompt with the data for plot generation
    plot_prompt = (
        f"{prompt}\n\n"
        f"Based on the following data, generate Python code using matplotlib to create the plot:\n{data}"
    )

    # Send request to ChatGPT to generate Python code for plotting
    headers = {
        "Authorization": f"Bearer {GPT4_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Generate Python code for data visualization using matplotlib. No explanation needed; just python code is sufficient as it would be directly executed to generate plots",
            },
            {"role": "user", "content": plot_prompt},
        ],
        "temperature": 0.0,
    }

    response = requests.post(CHATGPT_API_URL, headers=headers, json=data)
    result = response.json()

    python_code = result["choices"][0]["message"]["content"]
    return python_code


def execute_generated_code(python_code: str, showPopup: bool):
    local_vars = {}
    try:
        if showPopup:
            # Allow the plot to be displayed
            exec(python_code, {"plt": plt}, local_vars)
            return None  # No Base64 image if showing popup
        else:
            # Replace plt.show() with code to save the plot to img_buffer
            modified_code = python_code.replace(
                "plt.show()",
                "plt.savefig(img_buffer, format='png'); img_buffer.seek(0)",
            )

            # Prepare an in-memory buffer
            img_buffer = BytesIO()

            # Inject the buffer into the execution environment
            exec(
                modified_code,
                {
                    "plt": plt,
                    "BytesIO": BytesIO,
                    "base64": base64,
                    "img_buffer": img_buffer,
                },
                local_vars,
            )

            # Ensure the buffer contains data
            if img_buffer.getbuffer().nbytes == 0:
                print("Error: No data in the buffer after saving the plot.")
                return None

            # Encode the buffer content in Base64
            encoded_image = f"data:image/png;base64,{base64.b64encode(img_buffer.getvalue()).decode('utf-8')}"

            return encoded_image

    except Exception as e:
        print(f"Error executing generated code: {e}")
        return None
