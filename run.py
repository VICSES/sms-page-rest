import os
import base64

if __name__ == '__main__':
    os.environ['TOKEN_SECRET'] = str(base64.b64encode(b'secret'*11), 'utf-8')

from web import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
