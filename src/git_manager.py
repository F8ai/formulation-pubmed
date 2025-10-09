"""
Git Manager Module

Handles automatic Git commits and pushes during the download process.
"""

import subprocess
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class GitManager:
    """Manages Git operations for automatic commits and pushes"""
    
    def __init__(self, repo_path: str = ".", branch: str = "main"):
        self.repo_path = repo_path
        self.branch = branch
        self.commit_count = 0
        self.last_push_time = None
        
    async def commit_and_push_if_needed(self, stage: str, count: int, force_push: bool = False) -> bool:
        """
        Commit and push changes if conditions are met
        
        Args:
            stage: Current processing stage
            count: Number of items processed
            force_push: Force push even if conditions not met
            
        Returns:
            True if commit/push was performed
        """
        try:
            # Check if we should commit
            should_commit = self._should_commit(stage, count, force_push)
            
            if not should_commit:
                return False
            
            # Stage all changes
            await self._stage_changes()
            
            # Create commit message
            commit_message = self._create_commit_message(stage, count)
            
            # Commit changes
            success = await self._commit_changes(commit_message)
            if not success:
                return False
            
            self.commit_count += 1
            
            # Push if needed
            should_push = self._should_push(stage, count, force_push)
            if should_push:
                push_success = await self._push_changes()
                if push_success:
                    self.last_push_time = datetime.now()
                    logger.info(f"Successfully pushed changes to GitHub")
                    return True
                else:
                    logger.warning("Failed to push changes to GitHub")
                    return False
            else:
                logger.info(f"Committed changes locally (stage: {stage}, count: {count})")
                return True
                
        except Exception as e:
            logger.error(f"Error in commit/push process: {str(e)}")
            return False
    
    def _should_commit(self, stage: str, count: int, force_push: bool) -> bool:
        """Determine if we should commit based on stage and count"""
        if force_push:
            return True
        
        # Commit conditions based on stage
        commit_conditions = {
            'metadata': count % 10 == 0,  # Every 10 metadata entries
            'abstract': count % 5 == 0,   # Every 5 abstracts
            'fulltext': count % 3 == 0,   # Every 3 full texts
            'ocr': count % 2 == 0,        # Every 2 OCR completions
            'batch_complete': True,       # Always commit batch completions
            'status_update': True         # Always commit status updates
        }
        
        return commit_conditions.get(stage, False)
    
    def _should_push(self, stage: str, count: int, force_push: bool) -> bool:
        """Determine if we should push to GitHub"""
        if force_push:
            return True
        
        # Push conditions
        push_conditions = {
            'metadata': count % 50 == 0,  # Every 50 metadata entries
            'abstract': count % 25 == 0,  # Every 25 abstracts
            'fulltext': count % 10 == 0,  # Every 10 full texts
            'ocr': count % 5 == 0,        # Every 5 OCR completions
            'batch_complete': True,       # Always push batch completions
            'status_update': True,        # Always push status updates
            'hourly': self._is_hourly_push_needed()
        }
        
        return push_conditions.get(stage, False)
    
    def _is_hourly_push_needed(self) -> bool:
        """Check if we need to push based on time (hourly)"""
        if not self.last_push_time:
            return True
        
        time_since_last_push = datetime.now() - self.last_push_time
        return time_since_last_push.total_seconds() > 3600  # 1 hour
    
    async def _stage_changes(self) -> bool:
        """Stage all changes for commit"""
        try:
            # Add all changes
            result = subprocess.run(
                ['git', 'add', '.'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Error staging changes: {result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout while staging changes")
            return False
        except Exception as e:
            logger.error(f"Error staging changes: {str(e)}")
            return False
    
    async def _commit_changes(self, message: str) -> bool:
        """Commit staged changes"""
        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                if "nothing to commit" in result.stdout:
                    logger.info("No changes to commit")
                    return True
                else:
                    logger.error(f"Error committing changes: {result.stderr}")
                    return False
            
            logger.info(f"Committed changes: {message}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout while committing changes")
            return False
        except Exception as e:
            logger.error(f"Error committing changes: {str(e)}")
            return False
    
    async def _push_changes(self) -> bool:
        """Push changes to GitHub"""
        try:
            result = subprocess.run(
                ['git', 'push', 'origin', self.branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Error pushing changes: {result.stderr}")
                return False
            
            logger.info("Successfully pushed changes to GitHub")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout while pushing changes")
            return False
        except Exception as e:
            logger.error(f"Error pushing changes: {str(e)}")
            return False
    
    def _create_commit_message(self, stage: str, count: int) -> str:
        """Create commit message based on stage and count"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        messages = {
            'metadata': f"Add {count} article metadata entries - {timestamp}",
            'abstract': f"Process {count} article abstracts - {timestamp}",
            'fulltext': f"Download {count} full text articles - {timestamp}",
            'ocr': f"Complete OCR processing for {count} articles - {timestamp}",
            'batch_complete': f"Complete batch processing - {count} total articles - {timestamp}",
            'status_update': f"Update status page and metrics - {timestamp}",
            'hourly': f"Hourly backup - {count} articles processed - {timestamp}"
        }
        
        return messages.get(stage, f"Update processing stage {stage} - {count} items - {timestamp}")
    
    async def force_commit_and_push(self, message: str) -> bool:
        """Force commit and push with custom message"""
        try:
            # Stage changes
            await self._stage_changes()
            
            # Commit with custom message
            success = await self._commit_changes(message)
            if not success:
                return False
            
            # Push changes
            push_success = await self._push_changes()
            if push_success:
                self.last_push_time = datetime.now()
                logger.info(f"Force commit and push completed: {message}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in force commit/push: {str(e)}")
            return False
    
    async def get_git_status(self) -> Dict[str, Any]:
        """Get current Git status"""
        try:
            # Get status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Get last commit
            commit_result = subprocess.run(
                ['git', 'log', '-1', '--oneline'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Get branch info
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                'has_changes': len(status_result.stdout.strip()) > 0,
                'changes': status_result.stdout.strip().split('\n') if status_result.stdout.strip() else [],
                'last_commit': commit_result.stdout.strip() if commit_result.returncode == 0 else 'Unknown',
                'current_branch': branch_result.stdout.strip() if branch_result.returncode == 0 else 'Unknown',
                'commit_count': self.commit_count,
                'last_push_time': self.last_push_time.isoformat() if self.last_push_time else None
            }
            
        except Exception as e:
            logger.error(f"Error getting Git status: {str(e)}")
            return {
                'error': str(e),
                'has_changes': False,
                'changes': [],
                'last_commit': 'Unknown',
                'current_branch': 'Unknown',
                'commit_count': self.commit_count,
                'last_push_time': None
            }
    
    async def setup_git_config(self, name: str = "PubMed Scraper", email: str = "scraper@f8ai.com"):
        """Setup Git configuration for automated commits"""
        try:
            # Set user name
            subprocess.run(
                ['git', 'config', 'user.name', name],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10
            )
            
            # Set user email
            subprocess.run(
                ['git', 'config', 'user.email', email],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10
            )
            
            logger.info(f"Git configuration set: {name} <{email}>")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Git configuration: {str(e)}")
            return False