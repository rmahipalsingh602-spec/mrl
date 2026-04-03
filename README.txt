MRL quick Git setup

If Git shows a dubious ownership warning or push fails because no remote is set, run:

powershell -ExecutionPolicy Bypass -File scripts/fix_git_setup.ps1

To connect this project to GitHub in one step:

powershell -ExecutionPolicy Bypass -File scripts/fix_git_setup.ps1 -OriginUrl https://github.com/YOUR_USERNAME/YOUR_REPO.git

After that:

git add .
git commit -m "Launch MRL 3.1 with counted loops, boolean logic, and site refresh"
git push -u origin main
