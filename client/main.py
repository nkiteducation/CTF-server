import msgspec
import pathlib
import asyncio
import aiohttp
from rich.console import Console
from rich.table import Table
import uvloop


MANIFEST_PATH = pathlib.Path("./manifest.yaml")
console = Console()

class Flag(msgspec.Struct):
    zip: str
    web: str
    curl: str

class Manifest(msgspec.Struct):
    rpi: list[str]
    flag: Flag

def split_into_parts(s: str, n: int) -> list[str]:
    L = len(s)
    if n == 0: return []
    base = L // n
    remainder = L % n
    parts = []
    idx = 0
    for i in range(n):
        part_len = base + (1 if i < remainder else 0)
        parts.append(s[idx : idx + part_len])
        idx += part_len
    return parts

async def send_config(session: aiohttp.ClientSession, host: str, payload: dict):
    url = f"http://{host}/set-config"
    
    try:
        async with session.post(url, json=payload, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                password = data.get("zip_password", "N/A")
                return host, True, password
            else:
                return host, False, f"Error {response.status}"
    except Exception as e:
        return host, False, str(e)

async def main():
    # 1. Загрузка манифеста
    if not MANIFEST_PATH.exists():
        console.print("[bold red]Файл manifest.yaml не найден![/bold red]")
        return

    manifest = msgspec.yaml.decode(MANIFEST_PATH.read_bytes(), type=Manifest)

    rpis = manifest.rpi
    n = len(rpis)

    if n == 0:
        console.print("[yellow]В списке RPi нет хостов.[/yellow]")
        return

    # 2. Подготовка частей для каждого флага
    zip_parts = split_into_parts(manifest.flag.zip, n)
    web_parts = split_into_parts(manifest.flag.web, n)
    curl_parts = split_into_parts(manifest.flag.curl, n)

    console.print(f"[bold blue]Распределяем данные на {n} устройств...[/bold blue]\n")

    # 3. Отправка запросов
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(n):
            payload = {
                "zip": zip_parts[i],
                "web": web_parts[i],
                "curl": curl_parts[i]
            }
            tasks.append(send_config(session, rpis[i], payload))
        
        results = await asyncio.gather(*tasks)

    # 4. Красивый вывод результатов в таблицу
    table = Table(title="Результаты распределения флагов")
    table.add_column("RPi Host", style="cyan")
    table.add_column("Статус", justify="center")
    table.add_column("ZIP Password / Error", style="green")

    for host, success, info in results:
        status = "[green]OK[/green]" if success else "[red]FAIL[/red]"
        table.add_row(host, status, info)

    console.print(table)

if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        pass