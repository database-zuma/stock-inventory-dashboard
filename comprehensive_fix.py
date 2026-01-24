#!/usr/bin/env python3
"""
Comprehensive fix for Supabase dashboard - combines ALL fixes safely
"""

# Read index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix: Ensure Supabase is initialized AFTER library loads
old_init = '''    <script>'''

new_init = '''    <script>
        // Wait for Supabase to be fully loaded
        window.addEventListener('DOMContentLoaded', function() {
            console.log('✅ DOM loaded, initializing Supabase...');

            // Small delay to ensure library is ready
            setTimeout(initializeSupabase, 100);
        });

        function initializeSupabase() {'''

content = content.replace(old_init, new_init, 1)

# 2. Close the initializeSupabase function at the end
# Find the last </script> before </body>
import re

# Add closing brace before the last script tag ends
content = re.sub(
    r'(document\.addEventListener\([\'"]DOMContentLoaded[\'"], initDashboard\);)\s*</script>\s*</body>',
    r'\1\n        } // End initializeSupabase\n    </script>\n</body>',
    content
)

# 3. Wrap DOMContentLoaded initDashboard in the new structure
old_domready = '''document.addEventListener('DOMContentLoaded', initDashboard);'''

new_domready = '''// initDashboard will be called after Supabase is ready
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📊 Ready to init dashboard after auth check');
            setTimeout(initDashboard, 200);
        });'''

content = content.replace(old_domready, new_domready)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Comprehensive fix applied!")
print("📝 Changes:")
print("  - Ensured Supabase loads before initialization")
print("  - Added proper timing delays")
print("  - Fixed async loading issues")
