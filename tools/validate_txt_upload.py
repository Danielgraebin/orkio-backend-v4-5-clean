#!/usr/bin/env python3.11
"""
Script de validação oficial do upload TXT - ORKIO v3.4.X
Executa testes determinísticos e gera relatório em JSON
"""

import requests
import json
import sys
from datetime import datetime

API = "http://localhost:8001/api/v1"

def run_validation():
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    print("=" * 70)
    print("VALIDAÇÃO OFICIAL - Upload TXT ORKIO")
    print("=" * 70)
    print()
    
    # Login
    try:
        resp = requests.post(f"{API}/auth/login", json={
            "email": "admin@patro.ai",
            "password": "Passw0rd!"
        }, timeout=10)
        
        if resp.status_code != 200:
            print(f"❌ Login falhou: {resp.status_code}")
            results["login_error"] = resp.text
            return results
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login OK\n")
        
    except Exception as e:
        print(f"❌ Login exception: {e}")
        results["login_error"] = str(e)
        return results
    
    # Test 1: Upload test_ok.txt
    test1 = {
        "name": "Upload test_ok.txt",
        "status": "failed",
        "details": {}
    }
    results["tests"].append(test1)
    results["summary"]["total"] += 1
    
    print("TEST 1: Upload test_ok.txt")
    print("-" * 70)
    
    try:
        # Create test file
        test_content = "Olá Alfred,\nEste é um teste simples do ORKIO.\nVamos validar o upload TXT!\n"
        with open("/tmp/test_ok.txt", "w", encoding="utf-8") as f:
            f.write(test_content)
        
        with open("/tmp/test_ok.txt", "rb") as f:
            files = {"file": ("test_ok.txt", f, "text/plain")}
            data = {"tags": "validation,official", "agent_ids": "1"}
            
            resp = requests.post(
                f"{API}/admin/knowledge/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
        
        test1["details"]["status_code"] = resp.status_code
        test1["details"]["response"] = resp.json()
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        result = resp.json()
        
        if resp.status_code == 200 and result.get("status") == "vectorized" and result.get("chunks_count", 0) >= 1:
            test1["status"] = "passed"
            results["summary"]["passed"] += 1
            print(f"✅ TEST 1 PASSOU: status={result.get('status')}, chunks={result.get('chunks_count')}\n")
        else:
            results["summary"]["failed"] += 1
            print(f"❌ TEST 1 FALHOU: {result}\n")
            
    except Exception as e:
        test1["details"]["exception"] = str(e)
        results["summary"]["failed"] += 1
        print(f"❌ TEST 1 EXCEPTION: {e}\n")
    
    # Test 2: Upload empty.txt
    test2 = {
        "name": "Upload empty.txt",
        "status": "failed",
        "details": {}
    }
    results["tests"].append(test2)
    results["summary"]["total"] += 1
    
    print("TEST 2: Upload empty.txt")
    print("-" * 70)
    
    try:
        with open("/tmp/empty.txt", "w") as f:
            f.write("")
        
        with open("/tmp/empty.txt", "rb") as f:
            files = {"file": ("empty.txt", f, "text/plain")}
            data = {"tags": "validation,empty", "agent_ids": ""}
            
            resp = requests.post(
                f"{API}/admin/knowledge/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
        
        test2["details"]["status_code"] = resp.status_code
        test2["details"]["response"] = resp.json()
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        result = resp.json()
        
        # Should return error with reason
        if result.get("status") == "error":
            test2["status"] = "passed"
            results["summary"]["passed"] += 1
            print(f"✅ TEST 2 PASSOU: Erro tratado corretamente\n")
        else:
            results["summary"]["failed"] += 1
            print(f"❌ TEST 2 FALHOU: Deveria retornar erro\n")
            
    except Exception as e:
        test2["details"]["exception"] = str(e)
        results["summary"]["failed"] += 1
        print(f"❌ TEST 2 EXCEPTION: {e}\n")
    
    # Test 3: List documents
    test3 = {
        "name": "GET /admin/knowledge/list",
        "status": "failed",
        "details": {}
    }
    results["tests"].append(test3)
    results["summary"]["total"] += 1
    
    print("TEST 3: Listar documentos")
    print("-" * 70)
    
    try:
        resp = requests.get(f"{API}/admin/knowledge/list", headers=headers, timeout=10)
        
        test3["details"]["status_code"] = resp.status_code
        
        if resp.status_code == 200:
            data = resp.json()
            test3["details"]["total"] = data.get("total", 0)
            test3["status"] = "passed"
            results["summary"]["passed"] += 1
            print(f"Total documentos: {data.get('total')}")
            print(f"✅ TEST 3 PASSOU\n")
        else:
            results["summary"]["failed"] += 1
            print(f"❌ TEST 3 FALHOU: {resp.status_code}\n")
            
    except Exception as e:
        test3["details"]["exception"] = str(e)
        results["summary"]["failed"] += 1
        print(f"❌ TEST 3 EXCEPTION: {e}\n")
    
    # Summary
    print("=" * 70)
    print("RESUMO:")
    print(f"Total: {results['summary']['total']}")
    print(f"Passou: {results['summary']['passed']}")
    print(f"Falhou: {results['summary']['failed']}")
    print("=" * 70)
    
    return results

if __name__ == "__main__":
    results = run_validation()
    
    # Save JSON
    with open("/tmp/validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Resultados salvos em: /tmp/validation_results.json")
    
    # Exit with error code if any test failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

