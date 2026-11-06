import asyncio
import httpx

async def inspect():
    async with httpx.AsyncClient(timeout=15.0) as client:
        # HackerRank
        r = await client.get('https://boards-api.greenhouse.io/v1/boards/hackerrank/jobs?content=true')
        for j in r.json().get('jobs', []):
            loc = j.get('location', {}).get('name', '')
            print(f"HackerRank: {j['title']} | {loc} | {j['absolute_url']}")

        # Rubrik India
        r = await client.get('https://boards-api.greenhouse.io/v1/boards/rubrik/jobs?content=true')
        for j in r.json().get('jobs', []):
            loc = j.get('location', {}).get('name', '')
            if 'india' in loc.lower() or 'bangalore' in loc.lower():
                print(f"Rubrik: {j['title']} | {loc} | {j['absolute_url']}")

if __name__ == "__main__":
    asyncio.run(inspect())

