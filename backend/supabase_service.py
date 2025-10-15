from supabase import create_client, Client
import os
from typing import Optional
import base64
from datetime import datetime
import uuid

class SupabaseService:
    """
    Service for handling Supabase storage operations
    Stores violation snapshots and evidence images
    """
    
    def __init__(self):
        # Get Supabase credentials from environment
        supabase_url = os.environ.get('SUPABASE_URL', 'https://ukwnvvuqmiqrjlghgxnf.supabase.co')
        supabase_key = os.environ.get('SUPABASE_KEY', 
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrd252dnVxbWlxcmpsZ2hneG5mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA0MDQwMTEsImV4cCI6MjA3NTk4MDAxMX0.XhfmvtzuoEXXOrhenEFPzzVQNcIiZhcV3KAClmZnKEI')
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = "vinay"  # Changed to user's bucket name
        
        # Initialize bucket if it doesn't exist
        self._init_bucket()
    
    def _init_bucket(self):
        """
        Initialize the storage bucket for violation evidence
        """
        try:
            # Try to create bucket (will fail silently if exists)
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(b.name == self.bucket_name for b in buckets)
            
            if not bucket_exists:
                print(f"⚠️ Bucket '{self.bucket_name}' does not exist. Attempting to create...")
                try:
                    self.client.storage.create_bucket(
                        self.bucket_name,
                        options={"public": True, "fileSizeLimit": 52428800}  # 50MB limit
                    )
                    print(f"✅ Created Supabase bucket: {self.bucket_name}")
                except Exception as create_error:
                    print(f"❌ Could not create bucket: {create_error}")
                    print("⚠️ Please create the bucket manually in Supabase dashboard")
                    print(f"   Bucket name: {self.bucket_name}")
                    print(f"   Make it public and allow uploads")
            else:
                print(f"✅ Supabase bucket already exists: {self.bucket_name}")
        except Exception as e:
            print(f"⚠️ Bucket initialization error: {e}")
            print("📝 Will use base64 storage fallback")
    
    def upload_violation_snapshot(
        self, 
        snapshot_base64: str, 
        student_id: str, 
        session_id: str,
        violation_type: str
    ) -> Optional[str]:
        """
        Upload a violation snapshot to Supabase storage
        Returns the public URL of the uploaded image
        """
        try:
            # Decode base64 image
            if ',' in snapshot_base64:
                # Remove data:image/jpeg;base64, prefix if present
                snapshot_base64 = snapshot_base64.split(',')[1]
            
            image_data = base64.b64decode(snapshot_base64)
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{student_id}/{session_id}/{violation_type}_{timestamp}_{unique_id}.jpg"
            
            print(f"📤 Attempting to upload snapshot: {filename}")
            print(f"📦 Image data size: {len(image_data)} bytes")
            
            # Upload to Supabase with upsert to overwrite if exists
            response = self.client.storage.from_(self.bucket_name).upload(
                filename,
                image_data,
                file_options={
                    "content-type": "image/jpeg",
                    "upsert": "true"
                }
            )
            
            print(f"📤 Upload response: {response}")
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            
            print(f"✅ Uploaded snapshot successfully!")
            print(f"🔗 Public URL: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"❌ Snapshot upload error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_environment_check_image(
        self, 
        image_base64: str, 
        student_id: str
    ) -> Optional[str]:
        """
        Upload environment check image
        """
        try:
            image_data = base64.b64decode(image_base64)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{student_id}/environment_checks/env_check_{timestamp}.jpg"
            
            response = self.client.storage.from_(self.bucket_name).upload(
                filename,
                image_data,
                file_options={"content-type": "image/jpeg"}
            )
            
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            return public_url
            
        except Exception as e:
            print(f"Environment check upload error: {e}")
            return None
    
    def delete_snapshot(self, file_path: str) -> bool:
        """
        Delete a snapshot from storage
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    def list_student_snapshots(self, student_id: str, session_id: str) -> list:
        """
        List all snapshots for a specific student session
        """
        try:
            path = f"{student_id}/{session_id}/"
            files = self.client.storage.from_(self.bucket_name).list(path)
            return files
        except Exception as e:
            print(f"List snapshots error: {e}")
            return []

# Global instance
supabase_service = SupabaseService()
