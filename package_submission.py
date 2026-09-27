"""
Packages final submission zip according to official Unstop competition guidelines:
<team_name>_submission.zip
├── output/
│   ├── matching_results.tsv
│   └── candidate_pairs.tsv
├── code/
│   └── business_entity_resolution/
│       ├── src/
│       ├── README.md
│       └── requirements.txt
└── Documentation_template.md
"""

import os
import sys
import zipfile

def package_submission(team_name="Bhavana_Vemireddy", zip_name=None):
    if not zip_name:
        zip_name = f"{team_name}_submission.zip"
        
    print(f"Packaging {zip_name}...")
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1. output/ files
        zipf.write("output/matching_results.tsv", "output/matching_results.tsv")
        zipf.write("output/candidate_pairs.tsv", "output/candidate_pairs.tsv")
        
        # 2. code/business_entity_resolution/
        code_prefix = "code/business_entity_resolution/"
        zipf.write("README.md", f"{code_prefix}README.md")
        zipf.write("requirements.txt", f"{code_prefix}requirements.txt")
        
        if os.path.exists("generate_full_submission.py"):
            zipf.write("generate_full_submission.py", f"{code_prefix}generate_full_submission.py")

        for root, dirs, files in os.walk("src"):
            for file in files:
                if not file.endswith(('.pyc', '.pyo')):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, ".")
                    zipf.write(full_p, f"{code_prefix}{rel_p}")
                    
        # 3. Documentation_template.md
        if os.path.exists("Documentation_template.md"):
            zipf.write("Documentation_template.md", "Documentation_template.md")

    size_mb = os.path.getsize(zip_name) / (1024 * 1024)
    print(f"[OK] Successfully created {zip_name} ({size_mb:.2f} MB)")
    return zip_name

if __name__ == "__main__":
    t_name = sys.argv[1] if len(sys.argv) > 1 else "Bhavana_Vemireddy"
    package_submission(t_name)
