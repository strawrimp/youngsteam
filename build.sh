#!/bin/bash
cd "$(dirname "$0")"

for md in logs/*.md; do
    [ -f "$md" ] || continue
    html="${md%.md}.html"
    title=$(head -1 "$md" | sed 's/^# //')
    body=$(sed '1d' "$md" | sed 's/^## \(.*\)/<h3>\1<\/h3>/' | sed 's/^- \(.*\)/<li>\1<\/li>/' | sed 's/^  - \(.*\)/<li class="sub">\1<\/li>/')
    cat > "$html" << EOF
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} - Studio Ori</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>🏢 Studio Ori</h1>
        <p>Young's Team 작업 일지</p>
    </header>
    <nav>
        <a href="../index.html">메인</a>
        <a href="../guidelines.html">운영지침</a>
        <a href="../team.html">팀 소개</a>
    </nav>
    <main>
        <h2>${title}</h2>
        <ul class="log-list">${body}</ul>
    </main>
    <footer>
        <p>© 2026 Studio Ori</p>
    </footer>
    <script src="../js/main.js"></script>
</body>
</html>
EOF
    echo "Built: $html"
done
echo "Done!"
