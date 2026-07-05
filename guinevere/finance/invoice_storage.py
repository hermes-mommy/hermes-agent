"""
Finance Invoice Storage — S3 Uploader for Transaction Receipts

Uploads invoice/receipt images to IDCloudHost S3 via rclone
and stores URLs linked to finance transactions.

Usage:
    from guinevere.finance.invoice_storage import InvoiceStorage
    
    storage = InvoiceStorage()
    url = storage.upload_invoice(
        image_path="/path/to/invoice.jpg",
        transaction_id=48,
        amount=135765,
        description="API credit (apikey.fun)"
    )
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# S3 Configuration — IDCloudHost via Rclone
S3_BUCKET = "s3-guinevere"
S3_INVOICE_PREFIX = "invoices"
RCLONE_CONFIG = Path.home() / ".hermes" / "backup" / "rclone.conf"
RCLONE_REMOTE = "idcloudhost"


# Add hermes/bin to PATH for rclone
os.environ['PATH'] = str(Path.home() / '.hermes' / 'bin') + ':' + os.environ.get('PATH', '')


class InvoiceStorage:
    """Manages invoice/receipt image storage in IDCloudHost S3 via rclone."""
    
    def __init__(self):
        self.rclone_available = self._check_rclone()
    
    def _check_rclone(self) -> bool:
        """Check if rclone is available and configured."""
        if not RCLONE_CONFIG.exists():
            logger.warning(f"invoice_storage_rclone_config_not_found: {RCLONE_CONFIG}")
            return False
        
        try:
            result = subprocess.run(
                ["rclone", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("invoice_storage_rclone_available")
                return True
            else:
                logger.warning("invoice_storage_rclone_not_found")
                return False
        except Exception as e:
            logger.warning(f"invoice_storage_rclone_check_failed: {e}")
            return False
    
    def _generate_s3_key(
        self,
        transaction_id: int,
        amount: float,
        description: str,
        file_ext: str
    ) -> str:
        """Generate S3 object key for invoice."""
        today = date.today()
        # Sanitize description
        safe_desc = ''.join(c if c.isalnum() or c in '-_' else '_' for c in description)
        safe_desc = safe_desc[:50]  # Limit length
        
        # Format: invoices/YYYY/MM/YYYY-MM-DD_ID_AMOUNT_DESC.ext
        return (
            f"{S3_INVOICE_PREFIX}/{today.year}/{today.month:02d}/"
            f"{today.isoformat()}_{transaction_id}_{int(amount)}_{safe_desc}{file_ext}"
        )
    
    def upload_invoice(
        self,
        image_path: str,
        transaction_id: int,
        amount: float,
        description: str
    ) -> Optional[str]:
        """
        Upload invoice image to S3 via rclone and return public URL.
        
        Args:
            image_path: Local path to invoice image
            transaction_id: Finance transaction ID
            amount: Transaction amount
            description: Transaction description
        
        Returns:
            Public URL of uploaded invoice, or None on failure
        """
        if not self.rclone_available:
            logger.error("invoice_storage_rclone_not_available")
            return None
        
        if not os.path.exists(image_path):
            logger.error(f"invoice_storage_file_not_found: {image_path}")
            return None
        
        try:
            # Generate S3 key
            file_ext = Path(image_path).suffix or ".jpg"
            s3_key = self._generate_s3_key(transaction_id, amount, description, file_ext)
            
            # Upload via rclone
            source = f"{RCLONE_REMOTE}:{S3_BUCKET}/{s3_key}"
            
            result = subprocess.run(
                [
                    "rclone", "copy",
                    image_path,
                    source,
                    "--config", str(RCLONE_CONFIG)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"invoice_storage_rclone_upload_failed: {result.stderr}")
                return None
            
            # Generate public URL
            url = f"https://is3.cloudhost.id/{S3_BUCKET}/{s3_key}"
            
            logger.info(
                "invoice_storage_upload_success",
                extra={
                    "transaction_id": transaction_id,
                    "s3_key": s3_key,
                    "url": url
                }
            )
            
            return url
            
        except subprocess.TimeoutExpired:
            logger.error("invoice_storage_upload_timeout")
            return None
        except Exception as e:
            logger.error(f"invoice_storage_upload_failed: {e}")
            return None
    
    def get_invoice_url(self, transaction_id: int) -> Optional[str]:
        """Get invoice URL for a transaction from database."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from guinevere.finance.db import FinanceDB
            
            db = FinanceDB()
            result = db._execute(
                "SELECT invoice_url FROM finance.transactions WHERE id = %s",
                (transaction_id,)
            )
            
            if result and result[0].get('invoice_url'):
                return result[0]['invoice_url']
            
            return None
            
        except Exception as e:
            logger.error(f"invoice_storage_get_url_failed: {e}")
            return None
    
    def update_transaction_invoice(
        self,
        transaction_id: int,
        invoice_url: str
    ) -> bool:
        """Update transaction record with invoice URL."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from guinevere.finance.db import FinanceDB
            
            db = FinanceDB()
            db._execute(
                "UPDATE finance.transactions SET invoice_url = %s WHERE id = %s",
                (invoice_url, transaction_id)
            )
            
            logger.info(
                "invoice_storage_transaction_updated",
                extra={
                    "transaction_id": transaction_id,
                    "invoice_url": invoice_url
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"invoice_storage_update_failed: {e}")
            return False


# Singleton instance
_storage: Optional[InvoiceStorage] = None


def get_invoice_storage() -> InvoiceStorage:
    """Get singleton InvoiceStorage instance."""
    global _storage
    if _storage is None:
        _storage = InvoiceStorage()
    return _storage
