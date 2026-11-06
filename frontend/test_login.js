import axios from 'axios';

async function testLogin() {
    try {
        console.log("Testing login to http://127.0.0.1:8001/login...");
        const params = new URLSearchParams();
        params.append('username', 'security@fleitlab.com');
        params.append('password', 'password');

        const response = await axios.post('http://127.0.0.1:8001/login', params, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        console.log('Login success:', response.data);
    } catch (error) {
        console.error('Login failed:', error.response ? error.response.data : error.message);
    }
}

testLogin();
