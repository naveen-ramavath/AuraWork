import json
import logging

logger = logging.getLogger(__name__)

GROQ_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Retrieves the current date and time. Use this before scheduling any calendar events or checking emails.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_calendar_schedule",
            "description": "Fetches upcoming events from the user's Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to fetch. Defaults to 5."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_meeting",
            "description": "Creates a new calendar event (meeting) in the user's primary calendar and returns details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The title of the meeting."
                    },
                    "start_iso": {
                        "type": "string",
                        "description": "Start time in ISO format (e.g., '2026-06-28T09:00:00+05:30')."
                    },
                    "end_iso": {
                        "type": "string",
                        "description": "End time in ISO format."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional meeting description/agenda."
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional meeting location."
                    }
                },
                "required": ["summary", "start_iso", "end_iso"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_unread_emails",
            "description": "Retrieves unread emails from the user's Gmail inbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails to retrieve. Defaults to 5."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Retrieves and reads the full text of a specific Gmail email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Searches the user's Gmail emails using standard Gmail search syntax (e.g. from:Microsoft, subject:internship, is:unread).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query parameter using Gmail Query Syntax."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of search results to return. Defaults to 5."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reply_to_email",
            "description": "Replies to a specific email inside the same email thread using threadId and messageId references.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply_body": {
                        "type": "string",
                        "description": "The body text of the reply."
                    },
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email being replied to. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    }
                },
                "required": ["reply_body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forward_email",
            "description": "Forwards an email to a specified recipient address, preserving headers and forwarding attachments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "The email address to forward the email to."
                    },
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email being forwarded. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    }
                },
                "required": ["to_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_as_read",
            "description": "Marks a specific email as read by removing the unread label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_as_unread",
            "description": "Marks a specific email as unread by adding the unread label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "star_email",
            "description": "Stars or unstars a specific email by adding or removing the STARRED label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The unique ID of the email. Optional if email_index is given."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "The 1-based index of the email in the inbox list. Optional if message_id is given."
                    },
                    "star": {
                        "type": "boolean",
                        "description": "True to star the email, False to unstar it. Defaults to True."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text."
                    }
                },
                "required": ["to_email", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Creates an email draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text."
                    }
                },
                "required": ["to_email", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "post_slack_message",
            "description": "Posts a message to a specific Slack channel or team DM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "The name or ID of the channel (e.g. 'general' or 'dev-updates')."
                    },
                    "text": {
                        "type": "string",
                        "description": "The content of the message."
                    }
                },
                "required": ["channel", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_slack_mentions",
            "description": "Retrieves recent unread notifications and mentions for the user on Slack.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_assigned_jira_tickets",
            "description": "Fetches active, open Jira issues assigned to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of tickets to retrieve. Defaults to 5."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_work_hours",
            "description": "Logs time spent working on a specific Jira ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The Jira issue identifier (e.g., 'PROJ-101')."
                    },
                    "time_spent": {
                        "type": "string",
                        "description": "The duration to log (e.g., '1h 30m', '45m')."
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional description of the work done."
                    }
                },
                "required": ["issue_key", "time_spent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_jira_issue_ticket",
            "description": "Creates a new Jira issue ticket for tracking work.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "Project identifier (e.g. 'PROJ')."
                    },
                    "summary": {
                        "type": "string",
                        "description": "Short summary of the task."
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the work."
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Type of ticket (e.g., 'Task', 'Bug', 'Story'). Defaults to 'Task'."
                    }
                },
                "required": ["project_key", "summary", "description"]
            }
        }
    }
]


class AIEngine:

    @staticmethod
    def execute_gemini(
        chat,
        response,
        tools,
    ):
        """
        Executes the common tool-calling loop.
        """

        loop_limit = 5

        for _ in range(loop_limit):

            function_calls = []

            if response.candidates and response.candidates[0].content:

                for part in response.candidates[0].content.parts:

                    if part.function_call and part.function_call.name:
                        function_calls.append(part.function_call)

            if not function_calls:
                break

            tool_responses = []

            for call in function_calls:

                tool_name = call.name
                tool_args = dict(call.args)

                logger.info(
                    f"Model requested tool: {tool_name} with args: {tool_args}"
                )

                try:

                    tool_func = next(
                        t for t in tools
                        if t.__name__ == tool_name
                    )

                    result = tool_func(**tool_args)

                except Exception as err:

                    logger.exception(err)

                    result = json.dumps({
                        "status": "error",
                        "message": str(err)
                    })

                tool_responses.append({
                    "function_response": {
                        "name": tool_name,
                        "response": {
                            "result": result
                        }
                    }
                })

            response = chat.send_message(tool_responses)

        return response.text
    
    @staticmethod
    def execute(
        provider,
        **kwargs
    ):

        if provider == "gemini":
            return AIEngine.execute_gemini(**kwargs)

        elif provider == "groq":
            return AIEngine.execute_groq(**kwargs)

        elif provider == "openrouter":
            return AIEngine.execute_openrouter(**kwargs)

        elif provider == "deepseek":
            return AIEngine.execute_deepseek(**kwargs)

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def execute_openai_compatible(
        client,
        model_name,
        provider_name,
        user_message,
        tools,
        system_instruction,
    ):
        # Convert registered python tools to tool schemas
        tools_schemas = []
        for tool_func in tools:
            name = tool_func.__name__
            schema = next((s for s in GROQ_TOOL_SCHEMAS if s["function"]["name"] == name), None)
            if schema:
                tools_schemas.append(schema)
            else:
                logger.warning(f"No tool schema found for python function: {name}")

        messages = [
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        loop_limit = 5

        for _ in range(loop_limit):
            try:
                # Call completions API
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=tools_schemas if tools_schemas else None,
                    tool_choice="auto" if tools_schemas else None,
                    temperature=0.3,
                )
            except Exception as e:
                logger.exception(f"Error calling {provider_name} API: {e}")
                return f"❌ Sorry, I encountered an error communicating with {provider_name}: {str(e)}"

            response_message = completion.choices[0].message
            
            # Construct assistant message dict to append to history
            assistant_msg = {
                "role": "assistant",
                "content": response_message.content or ""
            }
            if response_message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            
            messages.append(assistant_msg)

            if not response_message.tool_calls:
                break

            # Execute tool calls
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = {}
                if tool_call.function.arguments:
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except Exception as e:
                        logger.error(f"Failed to parse arguments for tool {tool_name}: {e}")

                logger.info(
                    f"{provider_name} requested tool: {tool_name} with args: {tool_args}"
                )

                try:
                    tool_func = next(
                        t for t in tools
                        if t.__name__ == tool_name
                    )
                    result = tool_func(**tool_args)
                except Exception as err:
                    logger.exception(err)
                    result = json.dumps({
                        "status": "error",
                        "message": str(err)
                    })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result
                })

        return messages[-1]["content"]

    @staticmethod
    def execute_groq(
        client,
        user_message,
        tools,
        system_instruction,
    ):
        return AIEngine.execute_openai_compatible(
            client=client,
            model_name="llama-3.3-70b-versatile",
            provider_name="Groq",
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )

    @staticmethod
    def execute_openrouter(
        client,
        user_message,
        tools,
        system_instruction,
    ):
        return AIEngine.execute_openai_compatible(
            client=client,
            model_name="meta-llama/llama-3.3-70b-instruct",
            provider_name="OpenRouter",
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )

    @staticmethod
    def execute_deepseek(
        client,
        user_message,
        tools,
        system_instruction,
    ):
        return AIEngine.execute_openai_compatible(
            client=client,
            model_name="deepseek-chat",
            provider_name="DeepSeek",
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )