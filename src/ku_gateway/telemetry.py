"""Terminal telemetry for KU-Gateway."""

import time
from typing import Dict, Any, List, Tuple
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich import box
import logging

console = Console()

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

logger = logging.getLogger("ku-gateway")

class Telemetry:
    """Telemetry for KU-Gateway."""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_tokens = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0
        self.total_conflicts = 0
        self.total_latency = 0.0
    
    def print_startup(self, api_key: str, threshold: float, port: int = 8000):
        """Print startup banner."""
        tier = "enterprise" if api_key.startswith("ku_enterprise_") else "free" if api_key.startswith("ku_test_") else "paid"
        console.print(Panel(
            f"""🚀 [bold green]KU-Gateway v1.0.0[/bold green] starting...
            
[bold]✅ Loaded KU_API_KEY:[/bold] {api_key[:8]}... (tier: {tier})
[bold]⚙️ Decay threshold:[/bold] {threshold}
[bold]🛡️ Supported sources:[/bold] 14 (arxiv, github, stackoverflow, youtube, kaggle, ...)
[bold]🌐 Listening on:[/bold] http://localhost:{port}

[dim]💡 Change your LLM base_url to http://localhost:{port}[/dim]""",
            title="KU-Gateway",
            border_style="green"
        ))
    
    def print_request_summary(self, data: Dict[str, Any]):
        """Print a single request summary."""
        self.total_requests += 1
        
        # Build the table
        table = Table(title=f"📥 REQUEST #{self.total_requests} RECEIVED", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Timestamp", datetime.now().strftime("%H:%M:%S"))
        table.add_row("Original Tokens", f"{data['original_tokens']:,}")
        table.add_row("Clean Tokens", f"{data['clean_tokens']:,}")
        table.add_row("Tokens Saved", f"{data['tokens_saved']:,} ({data['savings_percentage']:.1f}%)")
        table.add_row("Cost Saved", f"${data.get('cost_saved', 0):.4f}")
        table.add_row("Chunks Evaluated", str(data['total_chunks']))
        table.add_row("Chunks Blocked", str(data['blocked_chunks']))
        table.add_row("Conflicts Detected", str(data.get('conflicts_detected', 0)))
        table.add_row("Average Decay", f"{data.get('avg_decay', 0):.2f}")
        
        console.print(table)
        
        # Print blocked chunks table if any
        if data.get('blocked_chunks', 0) > 0 and data.get('blocked_details'):
            self.print_blocked_chunks(data['blocked_details'])
        
        # Print conflicts if any
        if data.get('conflicts_detected', 0) > 0:
            self.print_conflicts(data.get('conflict_details', []))
        
        # Print cost savings highlight
        if data.get('tokens_saved', 0) > 0:
            console.print(Panel(
                f"[bold green]💰 Saved: {data['tokens_saved']:,} tokens | ${data.get('cost_saved', 0):.4f}[/bold green]",
                style="green"
            ))
    
    def print_blocked_chunks(self, blocked_details: List[Tuple[str, str, float]]):
        """Print blocked chunks table."""
        table = Table(title="🛑 BLOCKED CHUNKS", box=box.MINIMAL)
        table.add_column("Source", style="red")
        table.add_column("Title", style="dim")
        table.add_column("Decay", style="yellow")
        table.add_column("Reason", style="red")
        
        for source, title, decay in blocked_details[:5]:
            table.add_row(
                source,
                title[:40] + "..." if len(title) > 40 else title,
                f"{decay:.2f}",
                "> threshold"
            )
        
        if len(blocked_details) > 5:
            table.add_row("...", f"and {len(blocked_details) - 5} more", "", "")
        
        console.print(table)
    
    def print_conflicts(self, conflict_details: List[Dict]):
        """Print conflict detection table."""
        table = Table(title="⚠️ CONFLICTS DETECTED", box=box.MINIMAL)
        table.add_column("Source A", style="yellow")
        table.add_column("Source B", style="yellow")
        table.add_column("Conflict Type", style="red")
        
        for conflict in conflict_details[:3]:
            table.add_row(
                conflict.get("source_a", "Unknown"),
                conflict.get("source_b", "Unknown"),
                conflict.get("type", "Contradiction")
            )
        
        if len(conflict_details) > 3:
            table.add_row("...", f"and {len(conflict_details) - 3} more", "")
        
        console.print(table)
    
    def print_session_summary(self):
        """Print session summary."""
        uptime = time.time() - self.start_time
        
        table = Table(title=f"📊 SESSION SUMMARY", box=box.DOUBLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Requests", str(self.total_requests))
        table.add_row("Total Tokens", f"{self.total_tokens:,}")
        table.add_row("Tokens Saved", f"{self.total_tokens_saved:,} ({self.total_tokens_saved/self.total_tokens*100 if self.total_tokens > 0 else 0:.1f}%)")
        table.add_row("Cost Saved", f"${self.total_cost_saved:.2f}")
        table.add_row("Conflicts", str(self.total_conflicts))
        table.add_row("Avg Latency", f"{self.total_latency/self.total_requests if self.total_requests > 0 else 0:.0f}ms")
        table.add_row("Uptime", f"{uptime/60:.1f} minutes")
        
        console.print(table)
    
    def update(self, data: Dict[str, Any]):
        """Update session totals."""
        self.total_tokens += data.get('original_tokens', 0)
        self.total_tokens_saved += data.get('tokens_saved', 0)
        self.total_cost_saved += data.get('cost_saved', 0)
        self.total_conflicts += data.get('conflicts_detected', 0)
        self.total_latency += data.get('latency_ms', 0)