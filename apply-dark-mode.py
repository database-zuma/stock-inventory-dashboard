#!/usr/bin/env python3
"""
Dark Mode CSS Transformer for Zuma Inventory Dashboard
Safely replaces CSS without touching data or JavaScript
"""

import re
import os
from datetime import datetime

def apply_dark_mode():
    """Apply dark mode CSS to the inventory dashboard"""

    # File paths
    input_file = "dashboard_inventory_backup.html"
    css_file = "dark-mode-transform.css"
    output_file = "dashboard_inventory_dark.html"

    print("=" * 60)
    print("🌙 DARK MODE TRANSFORMER - Zuma Inventory Dashboard")
    print("=" * 60)
    print()

    # Check if files exist
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        return False

    if not os.path.exists(css_file):
        print(f"❌ Error: {css_file} not found!")
        return False

    # Get file sizes
    input_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    print(f"📄 Input file: {input_file} ({input_size:.1f} MB)")
    print(f"🎨 CSS file: {css_file}")
    print(f"💾 Output file: {output_file}")
    print()

    # Read dark mode CSS
    print("📖 Reading dark mode CSS...")
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            dark_css = f.read()
        # Remove the comment at the top of CSS file
        dark_css = re.sub(r'/\* DARK MODE TRANSFORMATION.*?\*/', '', dark_css, flags=re.DOTALL).strip()
        print(f"   ✅ Loaded {len(dark_css)} characters of CSS")
    except Exception as e:
        print(f"   ❌ Error reading CSS: {e}")
        return False

    # Read original HTML
    print()
    print("📖 Reading original dashboard HTML...")
    print("   ⏳ Please wait... (file is large)")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        print(f"   ✅ Loaded {len(html_content)} characters")
    except Exception as e:
        print(f"   ❌ Error reading HTML: {e}")
        return False

    # Find and replace CSS section
    print()
    print("🔄 Replacing CSS section...")

    # Pattern to match <style>...</style> including the tags
    style_pattern = r'<style>.*?</style>'

    # Check if style section exists
    if not re.search(style_pattern, html_content, re.DOTALL):
        print("   ❌ Error: Could not find <style> section!")
        return False

    # Count original matches
    original_match = re.search(style_pattern, html_content, re.DOTALL)
    original_css_length = len(original_match.group(0))
    print(f"   📊 Original CSS section: {original_css_length} characters")

    # Replace the CSS section
    new_style_section = f"<style>\n{dark_css}\n    </style>"
    html_content_dark = re.sub(
        style_pattern,
        new_style_section,
        html_content,
        count=1,  # Only replace first occurrence
        flags=re.DOTALL
    )

    # Verify replacement happened
    if html_content_dark == html_content:
        print("   ❌ Error: CSS replacement failed!")
        return False

    print(f"   📊 New CSS section: {len(new_style_section)} characters")
    print("   ✅ CSS replaced successfully")

    # Verify data integrity
    print()
    print("🔍 Verifying data integrity...")

    # Count table rows (data shouldn't change)
    original_rows = html_content.count('<tr')
    new_rows = html_content_dark.count('<tr')

    print(f"   📊 Table rows - Original: {original_rows}, New: {new_rows}")

    if original_rows != new_rows:
        print("   ⚠️  WARNING: Row count changed! Aborting...")
        return False

    # Count script tags (JavaScript shouldn't change)
    original_scripts = html_content.count('<script')
    new_scripts = html_content_dark.count('<script')

    print(f"   📊 Script tags - Original: {original_scripts}, New: {new_scripts}")

    if original_scripts != new_scripts:
        print("   ⚠️  WARNING: Script count changed! Aborting...")
        return False

    print("   ✅ Data integrity verified!")

    # Write output file
    print()
    print("💾 Writing dark mode dashboard...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content_dark)

        output_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"   ✅ Saved to {output_file} ({output_size:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Error writing file: {e}")
        return False

    # Summary
    print()
    print("=" * 60)
    print("✨ DARK MODE APPLIED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("📁 Files created:")
    print(f"   🌙 {output_file} - Dark mode version")
    print(f"   💾 {input_file} - Original (untouched)")
    print(f"   🔒 dashboard_inventory_original.html - Backup")
    print()
    print("🎨 What changed:")
    print("   ✅ Background: Dark navy (#0f172a)")
    print("   ✅ Cards: Glass-dark effect with backdrop blur")
    print("   ✅ Text: Light colors for readability")
    print("   ✅ Entity pills: Vibrant with glow effects")
    print("   ✅ Tables: Dark theme with bright headers")
    print("   ✅ Charts: Ready for dark background")
    print()
    print("🚀 Next steps:")
    print("   1. Open dashboard_inventory_dark.html in browser")
    print("   2. Test all filters and functionality")
    print("   3. Compare with original version")
    print()
    print("💡 Tip: Use Ctrl+F5 to hard refresh if colors look weird")
    print()

    return True

if __name__ == "__main__":
    try:
        success = apply_dark_mode()
        if success:
            print("✅ Done! Enjoy your dark mode dashboard! 🌙")
        else:
            print("❌ Dark mode transformation failed. Check errors above.")
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
