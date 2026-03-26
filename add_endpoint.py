import re

# Read the file
with open('app/app.py', 'r') as f:
    content = f.read()

# Find the pattern to replace
pattern = r'(    return jsonify\(\{\s*\'success\': True,\s*\'candidate\': latest\s*\}\))\s*(\n@app\.route\(\'/api/shortlist\')'

replacement = '''    return jsonify({
        'success': True,
        'candidate': latest
    })

@app.route('/api/candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get a specific candidate by ID."""
    db = get_db()
    row = db.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()

    if not row:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    candidate = dict(row)
    candidate['skills'] = json.loads(candidate['skills']) if candidate['skills'] else []

    return jsonify({
        'success': True,
        'candidate': candidate
    })

@app.route('/api/shortlist'''

# Replace
new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('app/app.py', 'w') as f:
    f.write(new_content)

print('Endpoint added successfully')