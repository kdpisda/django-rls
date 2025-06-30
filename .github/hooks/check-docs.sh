#!/bin/bash
# Pre-commit hook to check documentation changes

# Check if documentation files were modified
DOCS_CHANGED=$(git diff --cached --name-only | grep "^documentations/" | wc -l)

if [ $DOCS_CHANGED -gt 0 ]; then
    echo "📝 Documentation changes detected. Running checks..."
    
    # Check for broken internal links
    echo "Checking for broken internal links..."
    cd documentations
    
    # Simple check for broken markdown links
    BROKEN_LINKS=$(grep -r "\[.*\](.*.md)" docs/ | grep -v "http" | while read line; do
        FILE=$(echo "$line" | cut -d: -f1)
        LINK=$(echo "$line" | grep -o "(.*\.md)" | tr -d "()" | sed 's/#.*//')
        
        # Resolve relative path
        DIR=$(dirname "$FILE")
        FULL_PATH="$DIR/$LINK"
        
        if [ ! -f "$FULL_PATH" ] && [ ! -f "docs/$LINK" ]; then
            echo "Broken link in $FILE: $LINK"
        fi
    done)
    
    if [ ! -z "$BROKEN_LINKS" ]; then
        echo "❌ Found broken links:"
        echo "$BROKEN_LINKS"
        exit 1
    fi
    
    echo "✅ Documentation checks passed!"
    cd ..
fi