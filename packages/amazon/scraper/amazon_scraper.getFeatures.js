() => {
    feats_draw = document.querySelectorAll('#feature-bullets .a-list-item')

    feats = []
    for (i = 1; i <=feats.length; i++){
        feats.push(feats[i].innerText)
    }
}