import frappe
import os
import shutil

def make_all_files_public(doc, method):
    """Make all uploaded files public and move them to /public/files/."""
    doc.is_private = 0

    # Get original file_url (ex: /private/files/xyz.png)
    old_url = doc.file_url or ""

    # If file is already public, skip
    if "/private/" not in old_url:
        return

    # Create new public URL
    filename = os.path.basename(old_url)
    new_url = f"/files/{filename}"
    doc.file_url = new_url

    # Build full file system paths
    private_path = frappe.get_site_path("private", "files", filename)
    public_path = frappe.get_site_path("public", "files", filename)

    # Ensure target directory exists
    os.makedirs(os.path.dirname(public_path), exist_ok=True)

    # Move file from private → public if it exists
    if os.path.exists(private_path):
        shutil.move(private_path, public_path)
    else:
        frappe.logger().warning(f"Private file not found: {private_path}")
