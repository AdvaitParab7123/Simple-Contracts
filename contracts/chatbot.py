"""
Pulse AI Assistant - Chatbot Backend
Uses Google Gemini API for conversational AI
"""

import json
import os
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars

# System prompt that gives the AI context about the platform
SYSTEM_PROMPT = """You are Pulse Assistant, an AI helper for the Pulse Contract Management platform. 
You help users navigate the platform, answer questions about contracts, and provide guidance.

## About the Platform
Pulse is a contract management system that helps organizations:
- Create and manage contracts through a multi-step wizard
- Track contract lifecycle (Draft → Pending → Active → Expired/Terminated/Archived)
- Handle approval workflows
- Manage contract documents and versions
- Track clauses, deviations, and risks
- Record signatures

## Key Features & How to Use Them

### Creating a Contract
1. Click "New Contract" button on the dashboard or contracts list
2. Follow the wizard steps: Method → Upload → Name → Basic Info → Party Info → Dates → Value → Owner/Tags
3. Save as Draft or submit for approval

### Contract Statuses
- **Draft**: Initial state, still being created/edited
- **Pending**: Submitted, awaiting approval or action
- **Active**: Currently in effect
- **Expired**: Past the end date
- **Terminated**: Manually ended before expiry
- **Archived**: No longer active, kept for records

### Navigation
- **Dashboard** (/contracts/): Overview, pending items, quick stats
- **Contracts** (/contracts/list/): Full list with Draft/Pending/Repository tabs
- **Approvals** (/contracts/approvals/): Approval requests to review
- **Settings** (/contracts/configurations/): Manage contract types, tags, departments, clause playbook (admin only)

### Approvals
- Contract owners can request additional approvals from other users
- Designated approvers receive the request in their Approvals list
- Approvers can Approve or Reject with comments

### User Roles
- **Legal Admin**: Full access to everything
- **Legal User**: Can create/edit contracts, request approvals
- **Finance Viewer**: Read-only access to non-confidential contracts
- **User**: Can only see contracts shared with them

### Contract Details Page
From a contract detail page, users can:
- View/download the contract document
- Change status (if authorized)
- Add files and versions
- Request approvals
- Add clauses, deviations, risks
- Track signatures
- Share with other users or departments

## Response Guidelines
1. Be helpful, friendly, and concise
2. Use bullet points for lists
3. Provide specific navigation paths when relevant (e.g., "Go to Contracts → New Contract")
4. If unsure, suggest the user contact their administrator
5. For complex legal questions, recommend consulting with their legal team
6. Keep responses focused and actionable

Remember: You're helping users be more productive with the platform. Be encouraging and supportive!"""


def get_gemini_response(user_message, chat_history):
    """
    Get response from Google Gemini API
    """
    try:
        import google.generativeai as genai
        
        # Configure API key
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        
        if not api_key:
            return {
                'success': False,
                'response': "AI service is not configured. Please contact your administrator to set up the GEMINI_API_KEY."
            }
        
        genai.configure(api_key=api_key)
        
        # Create model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Build conversation history for context
        conversation = [{"role": "user", "parts": [SYSTEM_PROMPT]}]
        conversation.append({"role": "model", "parts": ["I understand. I'm Pulse Assistant, ready to help users with the contract management platform."]})
        
        # Add chat history (last few messages for context)
        for msg in chat_history[-6:]:  # Last 6 messages for context
            if msg.get('role') == 'user':
                conversation.append({"role": "user", "parts": [msg.get('content', '')]})
            elif msg.get('role') == 'assistant':
                conversation.append({"role": "model", "parts": [msg.get('content', '')]})
        
        # Add current message
        conversation.append({"role": "user", "parts": [user_message]})
        
        # Start chat and get response
        chat = model.start_chat(history=conversation[:-1])
        response = chat.send_message(user_message)
        
        return {
            'success': True,
            'response': response.text
        }
        
    except ImportError:
        return {
            'success': False,
            'response': "The AI module is not installed. Please run: pip install google-generativeai"
        }
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return {
            'success': False,
            'response': f"I'm having trouble connecting to the AI service. Please try again later."
        }


def get_fallback_response(user_message):
    """
    Provide helpful responses when AI is not available
    """
    message_lower = user_message.lower()
    
    # Navigation questions
    if any(word in message_lower for word in ['where', 'find', 'navigate', 'go to', 'how to get']):
        if 'contract' in message_lower and ('create' in message_lower or 'new' in message_lower):
            return "To create a new contract, click the **'New Contract'** button on the dashboard or go to Contracts → click 'New Contract'."
        if 'approval' in message_lower:
            return "You can find approvals by clicking the **Approvals** link in the sidebar, or go to /contracts/approvals/"
        if 'setting' in message_lower or 'config' in message_lower:
            return "Settings are available at **Settings** in the sidebar (admin only), or go to /contracts/configurations/"
    
    # Status questions
    if 'status' in message_lower:
        return """Contract statuses are:
• **Draft** - Being created/edited
• **Pending** - Awaiting approval
• **Active** - Currently in effect
• **Expired** - Past end date
• **Terminated** - Manually ended
• **Archived** - Kept for records"""
    
    # Approval questions
    if 'approval' in message_lower or 'approve' in message_lower:
        return """To manage approvals:
1. Open a contract detail page
2. Click **'Request Approval'** button
3. Select an approver and add a reason
4. The approver will see it in their Approvals list"""
    
    # Create contract
    if 'create' in message_lower and 'contract' in message_lower:
        return """To create a contract:
1. Click **'New Contract'** on the dashboard
2. Choose upload or template method
3. Fill in the wizard steps
4. Save as Draft or Submit for approval"""
    
    # Default response
    return """I can help you with:
• **Creating contracts** - "How do I create a contract?"
• **Navigation** - "Where can I find approvals?"
• **Statuses** - "What are the contract statuses?"
• **Approvals** - "How do approvals work?"

What would you like to know?"""


@require_http_methods(["POST"])
def chat_api(request):
    """
    API endpoint for chatbot
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        chat_history = data.get('history', [])
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'response': 'Please enter a message.'
            })
        
        # Try Gemini first, fall back to rule-based responses
        result = get_gemini_response(user_message, chat_history)
        
        if not result['success']:
            # Use fallback responses
            result = {
                'success': True,
                'response': get_fallback_response(user_message)
            }
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'response': 'Invalid request format.'
        })
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return JsonResponse({
            'success': False,
            'response': 'An error occurred. Please try again.'
        })

