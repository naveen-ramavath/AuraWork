import logging
from jira import JIRA
from config import Config

logger = logging.getLogger(__name__)

def get_jira_client(url: str = None, email: str = None, token: str = None) -> JIRA:
    """Returns an authenticated JIRA client connection."""
    jira_url = url or Config.JIRA_URL
    jira_email = email or Config.JIRA_EMAIL
    jira_token = token or Config.JIRA_API_TOKEN
    
    if not jira_url or not jira_email or not jira_token:
        raise ValueError("Jira connection details are incomplete.")
        
    return JIRA(server=jira_url, basic_auth=(jira_email, jira_token))

def get_assigned_jira_issues(limit: int = 5, url: str = None, email: str = None, token: str = None) -> list:
    """Fetches list of issues currently assigned to the authenticated user."""
    try:
        jira = get_jira_client(url, email, token)
        # Find the current user name or id
        myself = jira.myself()
        account_id = myself.get("accountId")
        
        jql = f"assignee = '{account_id}' AND statusCategory != Done ORDER BY updated DESC"
        issues = jira.search_issues(jql, maxResults=limit)
        
        result_list = []
        for issue in issues:
            result_list.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if hasattr(issue.fields, 'priority') else "Medium"
            })
        return result_list
    except Exception as e:
        logger.error(f"Error fetching assigned Jira issues: {e}")
        return []

def log_jira_work(issue_key: str, time_spent: str, comment: str = "", url: str = None, email: str = None, token: str = None) -> bool:
    """Logs time spent (e.g. '1h 30m') on a specific Jira issue."""
    try:
        jira = get_jira_client(url, email, token)
        jira.add_worklog(issue=issue_key, timeSpent=time_spent, comment=comment)
        return True
    except Exception as e:
        logger.error(f"Error logging work on issue {issue_key}: {e}")
        return False

def transition_jira_status(issue_key: str, transition_name: str, url: str = None, email: str = None, token: str = None) -> bool:
    """Transitions a Jira ticket status (e.g., 'In Progress', 'In Review', 'Done')."""
    try:
        jira = get_jira_client(url, email, token)
        transitions = jira.transitions(issue_key)
        
        transition_id = None
        for t in transitions:
            if t['name'].lower() == transition_name.lower():
                transition_id = t['id']
                break
                
        if transition_id:
            jira.transition_issue(issue_key, transition_id)
            return True
        else:
            logger.warning(f"Transition '{transition_name}' not found for issue {issue_key}.")
            return False
    except Exception as e:
        logger.error(f"Error transitioning status for issue {issue_key}: {e}")
        return False

def create_jira_ticket(project_key: str, summary: str, description: str, issue_type: str = "Task", url: str = None, email: str = None, token: str = None) -> str:
    """Creates a new Jira ticket and returns its key."""
    try:
        jira = get_jira_client(url, email, token)
        issue_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
        }
        new_issue = jira.create_issue(fields=issue_dict)
        return new_issue.key
    except Exception as e:
        logger.error(f"Error creating Jira ticket: {e}")
        return ""
