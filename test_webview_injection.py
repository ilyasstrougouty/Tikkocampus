import webview
import time
import threading

html = '''
<!DOCTYPE html>
<html>
<body>
  <h1>Test Popup</h1>
  <a href='https://www.google.com' target='_blank'>Link with target=_blank</a>
  <br><br>
  <button onclick="window.open('https://www.google.com', 'popup', 'width=600,height=600');">window.open()</button>
</body>
</html>
'''

def inject_js(window):
    time.sleep(1)
    # We can inject JS that intercepts window.open and clicks on target=_blank
    js = '''
        // 1. Intercept window.open
        window.oldOpen = window.open;
        window.open = function(url, name, features) {
            console.log('Intercepted window.open: ' + url);
            window.location.href = url;
            return window;
        };
        
        // 2. Intercept target='_blank' links
        document.addEventListener('click', function(e) {
            var target = e.target;
            while (target && target.tagName !== 'A') {
                target = target.parentNode;
            }
            if (target && target.tagName === 'A' && target.getAttribute('target') === '_blank') {
                e.preventDefault();
                console.log('Intercepted target=_blank: ' + target.href);
                window.location.href = target.href;
            }
        });
        document.title = 'Injected';
    '''
    try:
        window.evaluate_js(js)
        print('Injected!')
    except Exception as e:
        print('Inject Error:', e)

window = webview.create_window('Test Popup Intercept', html=html)
t = threading.Thread(target=inject_js, args=(window,))
t.daemon = True
t.start()
webview.start()
