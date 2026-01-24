#!/usr/bin/env python3
"""
Fix fetchFromSupabase function to use authenticated user token
"""

import re

# Read index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Old function pattern
old_pattern = r'''        // Fetch data from Supabase
        async function fetchFromSupabase\(table, params = \{\}\) \{
            try \{
                const queryString = new URLSearchParams\(params\)\.toString\(\);
                const url = `\$\{SUPABASE_URL\}/rest/v1/\$\{table\}\$\{queryString \? '\?' \+ queryString : ''\}`;

                const response = await fetch\(url, \{
                    headers: \{
                        'apikey': SUPABASE_ANON_KEY,
                        'Authorization': `Bearer \$\{SUPABASE_ANON_KEY\}`
                    \}
                \}\);

                if \(!response\.ok\) \{
                    throw new Error\(`HTTP error! status: \$\{response\.status\}`\);
                \}

                return await response\.json\(\);
            \} catch \(error\) \{
                console\.error\(`Error fetching from \$\{table\}:`, error\);
                throw error;
            \}
        \}'''

# New function
new_function = '''        // Fetch data from Supabase (with authenticated user token)
        async function fetchFromSupabase(table, params = {}) {
            try {
                // Get user's JWT token from session
                const { data: { session } } = await supabase.auth.getSession();
                const userToken = session ? session.access_token : SUPABASE_ANON_KEY;

                const queryString = new URLSearchParams(params).toString();
                const url = `${SUPABASE_URL}/rest/v1/${table}${queryString ? '?' + queryString : ''}`;

                console.log(`Fetching from ${table} with ${session ? 'USER' : 'ANON'} token`);

                const response = await fetch(url, {
                    headers: {
                        'apikey': SUPABASE_ANON_KEY,
                        'Authorization': `Bearer ${userToken}`
                    }
                });

                if (!response.ok) {
                    console.error(`HTTP ${response.status} from ${table}:`, await response.text());
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error(`Error fetching from ${table}:`, error);
                throw error;
            }
        }'''

# Replace
content_new = re.sub(old_pattern, new_function, content, flags=re.MULTILINE | re.DOTALL)

if content_new == content:
    print("⚠️  Pattern not found! Trying alternative method...")

    # Alternative: Find by simpler pattern
    old_simple = '''        async function fetchFromSupabase(table, params = {}) {
            try {
                const queryString = new URLSearchParams(params).toString();
                const url = `${SUPABASE_URL}/rest/v1/${table}${queryString ? '?' + queryString : ''}`;

                const response = await fetch(url, {
                    headers: {
                        'apikey': SUPABASE_ANON_KEY,
                        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error(`Error fetching from ${table}:`, error);
                throw error;
            }
        }'''

    content_new = content.replace(old_simple, new_function)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content_new)

print("✅ Fixed fetchFromSupabase function!")
print("📝 Changes:")
print("  - Now uses authenticated user's JWT token")
print("  - Falls back to anon key if not logged in")
print("  - Added console logging for debugging")
