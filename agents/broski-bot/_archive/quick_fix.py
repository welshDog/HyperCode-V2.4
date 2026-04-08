"""
BROski Bot v3.0 → v4.0 - Quick Quest Bug Fix
Adds missing 'title' column to quests table
Run this FIRST before any other updates
"""

import sqlite3
import sys

def fix_quests_table():
    """Add title column to quests table if missing."""
    
    print("=" * 80)
    print("🔧 BROski Bot - Quest Table Fix")
    print("=" * 80)
    print()
    
    try:
        # Connect to database
        print("📂 Connecting to database...")
        conn = sqlite3.connect('broski_bot.db')
        cursor = conn.cursor()
        
        # Check if title column exists
        cursor.execute("PRAGMA table_info(quests)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'title' in columns:
            print("✅ Title column already exists!")
            print("   No fix needed - you're good to go! 🎉")
            conn.close()
            return True
        
        print("⚠️  Title column missing - fixing now...")
        print()
        
        # Add title column
        print("1️⃣ Adding 'title' column...")
        cursor.execute("ALTER TABLE quests ADD COLUMN title TEXT DEFAULT 'Untitled Quest'")
        
        # Update existing quests with meaningful titles based on description
        print("2️⃣ Updating existing quest titles...")
        cursor.execute("""
            UPDATE quests 
            SET title = CASE 
                WHEN description LIKE '%focus%' THEN 'Complete Focus Session'
                WHEN description LIKE '%message%' THEN 'Send Messages'
                WHEN description LIKE '%command%' THEN 'Use Bot Commands'
                WHEN description LIKE '%daily%' THEN 'Daily Check-in'
                ELSE 'Complete Quest'
            END
            WHERE title = 'Untitled Quest' OR title IS NULL
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify fix
        cursor.execute("PRAGMA table_info(quests)")
        columns_after = [column[1] for column in cursor.fetchall()]
        
        if 'title' in columns_after:
            print()
            print("=" * 80)
            print("✅ SUCCESS! Quest table fixed!")
            print("=" * 80)
            print()
            print("Changes made:")
            print("  ✅ Added 'title' column to quests table")
            print("  ✅ Updated existing quests with titles")
            print("  ✅ Database committed")
            print()
            print("You can now:")
            print("  🚀 Run your bot without errors")
            print("  🎯 Create new quests with titles")
            print("  💰 Use /quests command")
            print()
            conn.close()
            return True
        else:
            print("❌ Fix verification failed!")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print()
    success = fix_quests_table()
    print()
    
    if success:
        print("🎉 Ready to go! Start your bot now! 🐶♾️")
        sys.exit(0)
    else:
        print("⚠️  Fix failed. Check the error messages above.")
        sys.exit(1)
