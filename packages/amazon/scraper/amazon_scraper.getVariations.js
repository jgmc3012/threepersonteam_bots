() => {
    containers = document.querySelectorAll('[id^="variation_"]')
    variations = []
    containers.array.forEach(container => {
        variation = {}

        typeDraw = container.querySelector('.a-row').innerText.split(':')
        variation['name'] = typeDraw[0].trim()
        
    });
}