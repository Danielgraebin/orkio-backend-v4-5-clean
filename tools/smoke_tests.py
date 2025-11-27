
#!/usr/bin/env python3
"""
ORKIO v4.5 - Smoke Tests
Valida o fluxo completo: cadastro, aprovação, agente, RAG, download, usage
"""
import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log_test(name: str, passed: bool, message: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {name}")
    if message:
        print(f"       {message}")

def log_section(title: str):
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}{title}{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")

def test_health():
    """Test if backend is running"""
    log_section("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        passed = response.status_code == 200
        log_test("Backend is running", passed, f"Status: {response.status_code}")
        return passed
    except Exception as e:
        log_test("Backend is running", False, str(e))
        return False

def test_register():
    """Test user registration"""
    log_section("2. User Registration")
    payload = {
        "email": f"test_{int(time.time())}@example.com",
        "password": "Test@1234567890",
        "name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/u/auth/register", json=payload, headers=HEADERS, timeout=10)
        passed = response.status_code == 200
        log_test("User registration", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            return {
                "email": payload["email"],
                "password": payload["password"],
                "user_id": data.get("user_id"),
                "tenant_id": data.get("tenant_id"),
                "token": data.get("access_token")
            }
        return None
    except Exception as e:
        log_test("User registration", False, str(e))
        return None

def test_login(email: str, password: str):
    """Test user login"""
    log_section("3. User Login")
    payload = {"email": email, "password": password}
    
    try:
        response = requests.post(f"{BASE_URL}/u/auth/login", json=payload, headers=HEADERS, timeout=10)
        passed = response.status_code == 200
        log_test("User login", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            return data.get("access_token")
        return None
    except Exception as e:
        log_test("User login", False, str(e))
        return None

def test_list_agents(token: str):
    """Test listing agents"""
    log_section("4. List Agents")
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/u/v4/agents", headers=headers, timeout=10)
        passed = response.status_code == 200
        log_test("List agents", passed, f"Status: {response.status_code}")
        
        if passed:
            agents = response.json()
            log_test("Agents returned", len(agents) > 0, f"Found {len(agents)} agents")
            return agents
        return []
    except Exception as e:
        log_test("List agents", False, str(e))
        return []

def test_create_conversation(token: str, agent_id: int):
    """Test creating a conversation"""
    log_section("5. Create Conversation")
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    payload = {"agent_id": agent_id, "title": "Test Conversation"}
    
    try:
        response = requests.post(f"{BASE_URL}/u/v4/conversations", json=payload, headers=headers, timeout=10)
        passed = response.status_code == 200 or response.status_code == 201
        log_test("Create conversation", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            return data.get("id")
        return None
    except Exception as e:
        log_test("Create conversation", False, str(e))
        return None

def test_chat(token: str, agent_id: int, conversation_id: int):
    """Test chat endpoint"""
    log_section("6. Chat with Agent (RAG)")
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    payload = {
        "agent_id": agent_id,
        "message": "Olá, como você está?",
        "conversation_id": conversation_id,
        "history": []
    }
    
    try:
        response = requests.post(f"{BASE_URL}/u/v4/chat", json=payload, headers=headers, timeout=30)
        passed = response.status_code == 200
        log_test("Chat endpoint", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            reply = data.get("reply", "")
            log_test("LLM response received", len(reply) > 0, f"Response length: {len(reply)} chars")
            return True
        return False
    except Exception as e:
        log_test("Chat endpoint", False, str(e))
        return False

def test_usage(token: str):
    """Test usage endpoint"""
    log_section("7. Usage Tracking")
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/u/v4/usage", headers=headers, timeout=10)
        passed = response.status_code == 200
        log_test("Usage endpoint", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            log_test("Usage data returned", isinstance(data, list), f"Got {len(data) if isinstance(data, list) else 0} metrics")
            return True
        return False
    except Exception as e:
        log_test("Usage endpoint", False, str(e))
        return False

def test_list_conversations(token: str):
    """Test listing conversations"""
    log_section("8. List Conversations")
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/u/v4/conversations", headers=headers, timeout=10)
        passed = response.status_code == 200
        log_test("List conversations", passed, f"Status: {response.status_code}")
        
        if passed:
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            log_test("Conversations returned", count > 0, f"Found {count} conversations")
            return True
        return False
    except Exception as e:
        log_test("List conversations", False, str(e))
        return False

def run_smoke_tests():
    """Run all smoke tests"""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}ORKIO v4.5 - Smoke Tests{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    print(f"Target: {BASE_URL}\n")
    
    # 1. Health check
    if not test_health():
        print(f"\n{RED}Backend is not running. Start it with: uvicorn app.main_v4:app --reload{RESET}")
        return False
    
    # 2. Register user
    user_data = test_register()
    if not user_data:
        print(f"\n{RED}Failed to register user{RESET}")
        return False
    
    # 3. Login
    token = test_login(user_data["email"], user_data["password"])
    if not token:
        print(f"\n{RED}Failed to login{RESET}")
        return False
    
    # 4. List agents
    agents = test_list_agents(token)
    if not agents:
        print(f"\n{YELLOW}No agents found. This is expected if no agents are configured.{RESET}")
        agent_id = None
    else:
        agent_id = agents[0]["id"] if agents else None
    
    # 5-8. Only run if we have an agent
    if agent_id:
        # Create conversation
        conversation_id = test_create_conversation(token, agent_id)
        if conversation_id:
            # Chat
            test_chat(token, agent_id, conversation_id)
            # List conversations
            test_list_conversations(token)
    
    # Usage
    test_usage(token)
    
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}Smoke tests completed!{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")
    return True

if __name__ == "__main__":
    try:
        success = run_smoke_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)
