"""
Dream Memory System - Four-stage memory consolidation process
Based on human sleep and memory consolidation
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import re

from rich.console import Console

from code_gen.memory import MemorySystem, Memory, MemoryType
from code_gen.core.client import ClaudeClient

console = Console()


@dataclass
class DreamPhase:
    """Dream phase result"""
    name: str
    description: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DreamMemorySystem:
    """
    Dream Memory System - Simulates human sleep memory consolidation
    
    Four stages:
    1. Fragment Collection - Collect raw conversation fragments
    2. Association Analysis - Find connections between fragments
    3. Knowledge Extraction - Extract reusable knowledge
    4. Memory Indexing - Store knowledge for retrieval
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.memdir_path = work_dir / ".code_gen" / "memdir"
        self.dream_dir = work_dir / ".code_gen" / "dreams"
        self.memories: List[Memory] = []
        self.dream_history: List[Dict] = []
        self._load_memories()
        self._load_dream_history()
    
    def _load_memories(self):
        """Load memories from disk"""
        self.memdir_path.mkdir(parents=True, exist_ok=True)
        
        memory_system = MemorySystem(self.work_dir)
        self.memories = memory_system.memories
    
    def _load_dream_history(self):
        """Load dream history from disk"""
        self.dream_dir.mkdir(parents=True, exist_ok=True)
        
        history_file = self.dream_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.dream_history = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load dream history: {e}[/yellow]")
                self.dream_history = []
    
    def _save_dream_history(self):
        """Save dream history to disk"""
        history_file = self.dream_dir / "history.json"
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.dream_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save dream history: {e}[/yellow]")
    
    def _collect_fragments(self) -> List[Dict]:
        """
        Stage 1: Fragment Collection
        
        Collect raw conversation fragments, code changes, user feedback
        without interpretation - just raw data collection
        """
        console.print("[bold]Stage 1: Fragment Collection[/bold]")
        
        fragments = []
        
        # Collect from memories
        for memory in self.memories:
            fragment = {
                "source": memory.type.value,
                "content": memory.content,
                "tags": memory.tags,
                "created_at": memory.created_at,
                "original_id": memory.id
            }
            fragments.append(fragment)
        
        # Collect from session history if available
        session_dir = self.work_dir / ".code_gen" / "sessions"
        if session_dir.exists():
            for session_file in session_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # Extract messages
                    if "messages" in session_data:
                        for msg in session_data["messages"]:
                            if msg.get("role") in ["user", "assistant"]:
                                fragment = {
                                    "source": "session",
                                    "content": msg.get("content", ""),
                                    "role": msg.get("role"),
                                    "timestamp": session_file.stem,
                                    "original_id": f"{session_file.stem}_{msg.get('role')}"
                                }
                                fragments.append(fragment)
                except Exception as e:
                    console.print(f"[dim]Skipped session file {session_file}: {e}[/dim]")
        
        console.print(f"  Collected {len(fragments)} fragments")
        
        return fragments
    
    def _analyze_associations(self, fragments: List[Dict]) -> List[Dict]:
        """
        Stage 2: Association Analysis
        
        Find connections between fragments
        e.g., a config question and an error might have the same root cause
        """
        console.print("[bold]Stage 2: Association Analysis[/bold]")
        
        associations = []
        
        # Group fragments by topic/keywords
        topic_groups: Dict[str, List[Dict]] = {}
        
        for fragment in fragments:
            # Extract keywords from content
            keywords = self._extract_keywords(fragment["content"])
            
            for keyword in keywords:
                if keyword not in topic_groups:
                    topic_groups[keyword] = []
                topic_groups[keyword].append(fragment)
        
        # Find associations
        for keyword, group in topic_groups.items():
            if len(group) > 1:
                association = {
                    "keyword": keyword,
                    "fragments": group,
                    "connection_type": "topic",
                    "insight": f"Found {len(group)} related fragments about '{keyword}'"
                }
                associations.append(association)
        
        # Analyze temporal patterns
        temporal_associations = self._analyze_temporal_patterns(fragments)
        associations.extend(temporal_associations)
        
        console.print(f"  Found {len(associations)} associations")
        
        return associations
    
    def _extract_keywords(self, text: str, limit: int = 5) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        text_lower = text.lower()
        
        # Common words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'dare', 'ought', 'used', 'it', 'its', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who', 'whom',
            'whose', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
            'now', 'here', 'there', 'then', 'once', 'if', 'because', 'as', 'until',
            'while', 'about', 'against', 'between', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'where',
            'why', 'how', 'any', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text_lower)
        
        # Filter stop words and count
        word_counts = {}
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:limit]]
    
    def _analyze_temporal_patterns(self, fragments: List[Dict]) -> List[Dict]:
        """Analyze temporal patterns in fragments"""
        associations = []
        
        # Group by timestamp
        time_groups: Dict[str, List[Dict]] = {}
        for fragment in fragments:
            timestamp = fragment.get("created_at", fragment.get("timestamp", ""))
            if timestamp:
                # Group by date
                date = timestamp[:10]  # YYYY-MM-DD
                if date not in time_groups:
                    time_groups[date] = []
                time_groups[date].append(fragment)
        
        # Find patterns
        for date, group in time_groups.items():
            if len(group) > 2:
                association = {
                    "keyword": f"temporal_{date}",
                    "fragments": group,
                    "connection_type": "temporal",
                    "insight": f"Multiple interactions on {date}: {len(group)} events"
                }
                associations.append(association)
        
        return associations
    
    def _extract_knowledge(self, fragments: List[Dict], associations: List[Dict]) -> List[Dict]:
        """
        Stage 3: Knowledge Extraction
        
        Extract reusable knowledge from fragments and associations
        """
        console.print("[bold]Stage 3: Knowledge Extraction[/bold]")
        
        knowledge_base = []
        
        # Extract from fragments
        for fragment in fragments:
            knowledge = self._extract_from_fragment(fragment)
            if knowledge:
                knowledge_base.append(knowledge)
        
        # Extract from associations
        for association in associations:
            knowledge = self._extract_from_association(association)
            if knowledge:
                knowledge_base.append(knowledge)
        
        console.print(f"  Extracted {len(knowledge_base)} knowledge items")
        
        return knowledge_base
    
    def _extract_from_fragment(self, fragment: Dict) -> Optional[Dict]:
        """Extract knowledge from a single fragment"""
        content = fragment.get("content", "")
        
        # Skip empty content
        if not content.strip():
            return None
        
        # Extract problem-solution pairs
        knowledge = {
            "type": "fragment",
            "source": fragment.get("source", "unknown"),
            "original_id": fragment.get("original_id", ""),
            "tags": fragment.get("tags", []),
            "content": content,
            "extracted_knowledge": content[:500],  # Extract first 500 chars as knowledge
            "confidence": 0.8,
            "timestamp": fragment.get("created_at", fragment.get("timestamp", ""))
        }
        
        return knowledge
    
    def _extract_from_association(self, association: Dict) -> Optional[Dict]:
        """Extract knowledge from an association"""
        fragments = association.get("fragments", [])
        
        if not fragments:
            return None
        
        # Combine fragment contents
        combined_content = "\n\n".join(
            f"[{f.get('source', 'unknown')}]: {f.get('content', '')[:200]}"
            for f in fragments
        )
        
        # Generate insight
        insight = f"Connected {len(fragments)} fragments about '{association.get('keyword', 'unknown')}'"
        
        knowledge = {
            "type": "association",
            "keyword": association.get("keyword", ""),
            "connection_type": association.get("connection_type", "unknown"),
            "insight": insight,
            "combined_content": combined_content,
            "confidence": 0.9,
            "timestamp": datetime.now().isoformat()
        }
        
        return knowledge
    
    def _index_memories(self, knowledge_base: List[Dict]) -> List[Dict]:
        """
        Stage 4: Memory Indexing
        
        Store knowledge in structured format for retrieval
        """
        console.print("[bold]Stage 4: Memory Indexing[/bold]")
        
        indexed_memories = []
        
        for knowledge in knowledge_base:
            # Create structured memory
            memory = {
                "id": f"dream_{len(indexed_memories)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "dream_insight",
                "content": knowledge.get("extracted_knowledge", knowledge.get("insight", "")),
                "tags": knowledge.get("tags", []) + [knowledge.get("type", "unknown")],
                "metadata": {
                    "source": knowledge.get("source", "unknown"),
                    "original_id": knowledge.get("original_id", ""),
                    "confidence": knowledge.get("confidence", 0),
                    "connection_type": knowledge.get("connection_type", ""),
                    "timestamp": knowledge.get("timestamp", "")
                },
                "created_at": datetime.now().isoformat()
            }
            
            indexed_memories.append(memory)
            
            # Save to disk
            self._save_indexed_memory(memory)
        
        console.print(f"  Indexed {len(indexed_memories)} memories")
        
        return indexed_memories
    
    def _save_indexed_memory(self, memory: Dict):
        """Save indexed memory to disk"""
        memory_path = self.memdir_path / "dream" / f"{memory['id']}.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = f"""# Dream Insight: {memory['id']}

## Content
{memory['content']}

## Metadata
- Type: {memory['type']}
- Source: {memory['metadata'].get('source', 'unknown')}
- Original ID: {memory['metadata'].get('original_id', '')}
- Confidence: {memory['metadata'].get('confidence', 0)}
- Connection Type: {memory['metadata'].get('connection_type', '')}
- Created: {memory['created_at']}

## Tags
{', '.join(memory['tags'])}
"""
        
        try:
            with open(memory_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save memory {memory['id']}: {e}[/yellow]")
    
    async def run_dream_process(self) -> Dict:
        """
        Run the complete four-stage dream process
        
        Returns:
            Dictionary containing all dream results
        """
        console.print("\n[bold]Starting Dream Memory Process[/bold]")
        console.print("=" * 60)
        
        # Stage 1: Fragment Collection
        console.print("\n[bold blue]Phase 1: Fragment Collection[/bold blue]")
        fragments = self._collect_fragments()
        
        if not fragments:
            console.print("[yellow]No fragments to process. Dream process skipped.[/yellow]")
            return {"status": "skipped", "message": "No fragments found"}
        
        # Stage 2: Association Analysis
        console.print("\n[bold blue]Phase 2: Association Analysis[/bold blue]")
        associations = self._analyze_associations(fragments)
        
        # Stage 3: Knowledge Extraction
        console.print("\n[bold blue]Phase 3: Knowledge Extraction[/bold blue]")
        knowledge_base = self._extract_knowledge(fragments, associations)
        
        if not knowledge_base:
            console.print("[yellow]No knowledge extracted. Dream process skipped.[/yellow]")
            return {"status": "skipped", "message": "No knowledge extracted"}
        
        # Stage 4: Memory Indexing
        console.print("\n[bold blue]Phase 4: Memory Indexing[/bold blue]")
        indexed_memories = self._index_memories(knowledge_base)
        
        # Generate summary
        summary = self._generate_summary(fragments, associations, knowledge_base, indexed_memories)
        
        # Save dream result
        dream_result = {
            "timestamp": datetime.now().isoformat(),
            "stages": {
                "fragment_collection": len(fragments),
                "association_analysis": len(associations),
                "knowledge_extraction": len(knowledge_base),
                "memory_indexing": len(indexed_memories)
            },
            "summary": summary,
            "indexed_memories": indexed_memories
        }
        
        # Save to dream history
        self.dream_history.append(dream_result)
        self._save_dream_history()
        
        # Save full dream result
        self._save_dream_result(dream_result)
        
        console.print("\n" + "=" * 60)
        console.print("[bold green]Dream Process Complete![/bold green]")
        console.print(f"  Fragments: {len(fragments)}")
        console.print(f"  Associations: {len(associations)}")
        console.print(f"  Knowledge Items: {len(knowledge_base)}")
        console.print(f"  Indexed Memories: {len(indexed_memories)}")
        
        return dream_result
    
    def _generate_summary(self, fragments: List[Dict], associations: List[Dict], 
                         knowledge_base: List[Dict], indexed_memories: List[Dict]) -> str:
        """Generate dream summary"""
        summary = f"""# Dream Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics
- Fragments Collected: {len(fragments)}
- Associations Found: {len(associations)}
- Knowledge Items Extracted: {len(knowledge_base)}
- Memories Indexed: {len(indexed_memories)}

## Key Insights
"""
        
        # Add top insights
        for knowledge in knowledge_base[:5]:
            content = knowledge.get("extracted_knowledge", knowledge.get("insight", ""))[:200]
            summary += f"- {content}\n"
        
        summary += "\n## Connections\n"
        for association in associations[:5]:
            summary += f"- {association.get('insight', 'Unknown connection')}\n"
        
        summary += "\n## Next Steps\n"
        summary += "- Review indexed memories for reference\n"
        summary += "- Update project documentation based on insights\n"
        summary += "- Create new memories for important learnings\n"
        
        return summary
    
    def _save_dream_result(self, dream_result: Dict):
        """Save dream result to file"""
        dream_file = self.dream_dir / f"dream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(dream_file, 'w', encoding='utf-8') as f:
                json.dump(dream_result, f, indent=2, ensure_ascii=False)
            
            console.print(f"\n[dim]Dream result saved to: {dream_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save dream result: {e}[/yellow]")
