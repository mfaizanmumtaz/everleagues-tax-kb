
import asyncio
import httpx
import time
import random
import os
import json
from datetime import datetime
from typing import List, Dict

# Configuration
BASE_URL = "http://localhost:8000"
SEARCH_ENDPOINT = f"{BASE_URL}/api/search/rag"
UPLOAD_ENDPOINT = f"{BASE_URL}/api/upload"
TEST_PDF_PATH = r"i1040gi.pdf"
OUTPUT_FILE = "load_test_report.txt"

# Simulation Parameters
NUM_SEARCH_REQUESTS = 50
NUM_UPLOAD_REQUESTS = 20
CONCURRENCY = 10

# Search Queries
QUERIES = [
    "tax brackets 2024",
    "deductions for home office",
    "capital gains tax rate",
    "child tax credit eligibility",
    "filing status standard deduction",
    "crypto tax reporting",
    "self-employment tax",
    "IRA contribution limits",
    "student loan interest deduction",
    "gift tax exclusions"
]

results = {
    "search": {"success": 0, "failed": 0, "times": []},
    "upload": {"success": 0, "failed": 0, "times": []}
}

async def perform_search(client: httpx.AsyncClient, query: str):
    start_time = time.time()
    try:
        payload = {
            "query": query,
            "filters": None,
            "search_quality_controls": None,
            "generate_answer": False
        }
        response = await client.post(SEARCH_ENDPOINT, json=payload)
        
        if response.status_code == 200:
            results["search"]["success"] += 1
            results["search"]["times"].append(time.time() - start_time)
        else:
            results["search"]["failed"] += 1
            print(f"Search '{query}' - FAILED: {response.status_code} - {response.text}")
            
    except Exception as e:
        results["search"]["failed"] += 1
        print(f"Search '{query}' - EXCEPTION: {str(e)}")

async def perform_upload(client: httpx.AsyncClient, file_path: str):
    start_time = time.time()
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            results["upload"]["failed"] += 1
            return

        filename = os.path.basename(file_path)
        
        # Metadata
        metadata = {
            "jurisdiction": "federal",
            "title": f"Load Test Upload {random.randint(1, 1000)}",
            "doc_type": "form",
            "tax_year": 2024
        }
        
        # Read file content safely
        with open(file_path, 'rb') as f:
            file_content = f.read()

        files = {
            'file': (filename, file_content, 'application/pdf')
        }
        data = {
            'metadata': json.dumps(metadata)
        }
        
        response = await client.post(UPLOAD_ENDPOINT, files=files, data=data)
        
        if response.status_code == 201:
            results["upload"]["success"] += 1
            results["upload"]["times"].append(time.time() - start_time)
        else:
            results["upload"]["failed"] += 1
            print(f"Upload - FAILED: {response.status_code} - {response.text}")

    except Exception as e:
        results["upload"]["failed"] += 1
        print(f"Upload - EXCEPTION: {str(e)}")

async def run_load_test():
    print(f"Starting load test...")
    print(f"Target: {BASE_URL}")
    print(f"Search Requests: {NUM_SEARCH_REQUESTS}")
    print(f"Upload Requests: {NUM_UPLOAD_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")
    
    # Resolve absolute path for PDF
    abs_pdf_path = os.path.abspath(TEST_PDF_PATH)
    if not os.path.exists(abs_pdf_path):
        print(f"Error: PDF file not found at {abs_pdf_path}")
        # Try finding it relative to current working directory if script is run from root
        potential_path = os.path.abspath("data/f1040s2.pdf")
        if os.path.exists(potential_path):
            abs_pdf_path = potential_path
            print(f"Found PDF at {abs_pdf_path}")
        else:
            print("Could not find test PDF. Aborting.")
            return

    print(f"Using PDF: {abs_pdf_path}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Probe
        try:
            await client.get(f"{BASE_URL}/")
            print("Server is reachable.")
        except Exception:
            print("Warning: Server might be down or not running at localhost:8000")

        # Concurrency control
        sem = asyncio.Semaphore(CONCURRENCY)
        
        async def bound_search(q):
            async with sem:
                await perform_search(client, q)

        async def bound_upload(f):
            async with sem:
                await perform_upload(client, f)

        all_tasks = []
        for _ in range(NUM_SEARCH_REQUESTS):
            all_tasks.append(bound_search(random.choice(QUERIES)))
        for _ in range(NUM_UPLOAD_REQUESTS):
            all_tasks.append(bound_upload(abs_pdf_path))
            
        random.shuffle(all_tasks)
        
        start_total = time.time()
        await asyncio.gather(*all_tasks)
        end_total = time.time()
        
        duration = end_total - start_total
        generate_report(duration)

def generate_report(duration):
    lines = []
    lines.append("="*50)
    lines.append(f"LOAD TEST REPORT - {datetime.now().isoformat()}")
    lines.append("="*50)
    lines.append(f"Total Duration: {duration:.2f} seconds")
    lines.append(f"Concurrency level: {CONCURRENCY}")
    lines.append("")
    
    # Search Stats
    s_success = results["search"]["success"]
    s_failed = results["search"]["failed"]
    s_total = s_success + s_failed
    s_times = results["search"]["times"]
    if s_times:
        s_avg = sum(s_times) / len(s_times)
        s_max = max(s_times)
        s_min = min(s_times)
    else:
        s_avg = s_max = s_min = 0

    lines.append(f"SEARCH API Results:")
    lines.append(f"  Total Requests: {s_total}")
    lines.append(f"  Success: {s_success}")
    lines.append(f"  Failed: {s_failed}")
    lines.append(f"  Avg Latency: {s_avg:.4f}s")
    lines.append(f"  Max Latency: {s_max:.4f}s")
    lines.append(f"  Min Latency: {s_min:.4f}s")
    if duration > 0:
        lines.append(f"  Throughput: {s_total/duration:.2f} req/s")
    lines.append("")

    # Upload Stats
    u_success = results["upload"]["success"]
    u_failed = results["upload"]["failed"]
    u_total = u_success + u_failed
    u_times = results["upload"]["times"]
    if u_times:
        u_avg = sum(u_times) / len(u_times)
        u_max = max(u_times)
        u_min = min(u_times)
    else:
        u_avg = u_max = u_min = 0

    lines.append(f"UPLOAD API Results:")
    lines.append(f"  Total Requests: {u_total}")
    lines.append(f"  Success: {u_success}")
    lines.append(f"  Failed: {u_failed}")
    lines.append(f"  Avg Latency: {u_avg:.4f}s")
    lines.append(f"  Max Latency: {u_max:.4f}s")
    lines.append(f"  Min Latency: {u_min:.4f}s")
    if duration > 0:
        lines.append(f"  Throughput: {u_total/duration:.2f} req/s")
    
    report_text = "\n".join(lines)
    print("\n" + report_text)
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(report_text)
    print(f"\nReport saved to {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    asyncio.run(run_load_test())
