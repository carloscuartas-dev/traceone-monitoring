# TraceOne Monitoring API - Postman Testing Guide

This directory contains a complete Postman setup for testing the TraceOne D&B monitoring service APIs.

## 📦 **What's Included**

- **TraceOne_Monitoring_API.postman_collection.json** - Complete API collection with automated tests
- **TraceOne_Environments.postman_environment.json** - Environment variables for different testing scenarios
- **README.md** - This comprehensive testing guide

## 🚀 **Quick Setup**

### **Step 1: Import Files into Postman**

1. Open Postman
2. Click **Import** button
3. Import both files:
   - `TraceOne_Monitoring_API.postman_collection.json`
   - `TraceOne_Environments.postman_environment.json`

### **Step 2: Configure Environment Variables**

1. Select **"TraceOne Development Environment"** from environment dropdown
2. Click the **eye icon** to view/edit environment variables
3. Update the required credentials:

```
client_id: your_actual_client_id_from_dnb
client_secret: your_actual_client_secret_from_dnb
base_url: https://plus.dnb.com/v1 (or your sandbox URL)
```

### **Step 3: Run Your First Test**

1. Open the **TraceOne Monitoring API** collection
2. Navigate to **Authentication > Get Access Token**
3. Click **Send**
4. Verify the access token is automatically stored

## 📋 **Collection Structure**

### **1. Authentication**
- **Get Access Token** - OAuth2 client credentials flow
- Automatically stores token for subsequent requests
- Tests token validity and expiration

### **2. Registration Management**
- **Create Registration** - Create new monitoring registrations
- **Get Registration Status** - Check registration details
- **List All Registrations** - View all your registrations

### **3. DUNS Management**
- **Add Single DUNS** - Add individual DUNS numbers
- **Add Multiple DUNS (Batch)** - Batch add using CSV format
- **Export DUNS List** - Get list of monitored DUNS
- **Remove DUNS** - Remove DUNS from monitoring

### **4. Monitoring Control**
- **Activate Monitoring** - Start monitoring notifications
- **Suppress Monitoring** - Temporarily pause monitoring

### **5. Pull API**
- **Pull Notifications** - Retrieve available notifications
- **Pull with Replay** - Get historical notifications
- **Get Pull Statistics** - Monitor pull metrics
- **Acknowledge Notifications** - Mark notifications as processed

### **6. Health Checks**
- **API Health Check** - Verify API availability
- **Service Status** - Get detailed system status

## 🔧 **Environment Variables**

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | TraceOne API base URL | `https://plus.dnb.com/v1` |
| `client_id` | OAuth2 client ID | `your_client_id` |
| `client_secret` | OAuth2 client secret | `your_client_secret` |
| `access_token` | Auto-stored access token | `eyJ0eXAi...` |
| `registration_reference` | Test registration name | `TraceOne_Test_Registration_123456` |
| `test_duns` | Primary test DUNS | `123456789` |
| `test_duns_2` | Secondary test DUNS | `987654321` |
| `test_duns_3` | Third test DUNS | `555666777` |

## 🧪 **Testing Scenarios**

### **Scenario 1: Basic Workflow Test**

Run these requests in order:

1. **Authentication > Get Access Token**
2. **Registration Management > Create Registration**
3. **DUNS Management > Add Single DUNS**
4. **Monitoring Control > Activate Monitoring**
5. **Pull API > Pull Notifications**

### **Scenario 2: Batch Operations Test**

1. **Authentication > Get Access Token**
2. **Registration Management > Create Registration**
3. **DUNS Management > Add Multiple DUNS (Batch)**
4. **DUNS Management > Export DUNS List**
5. **Pull API > Pull Notifications**

### **Scenario 3: Complete Portfolio Test**

```javascript
// Pre-request script for portfolio testing
pm.collectionVariables.set('registration_reference', 'Portfolio_Test_' + Date.now());

// Test multiple DUNS
pm.collectionVariables.set('test_duns', '123456789');
pm.collectionVariables.set('test_duns_2', '987654321');
pm.collectionVariables.set('test_duns_3', '555666777');
```

1. Create Registration
2. Add multiple DUNS in batch
3. Activate monitoring
4. Pull notifications
5. Acknowledge notifications

## ✅ **Automated Tests**

Each request includes comprehensive automated tests:

### **Response Validation**
```javascript
pm.test('Status code is 200', function () {
    pm.response.to.have.status(200);
});

pm.test('Response has required fields', function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('access_token');
    pm.expect(jsonData).to.have.property('expires_in');
});
```

### **Data Flow Testing**
```javascript
// Store values for subsequent requests
var jsonData = pm.response.json();
if (jsonData.access_token) {
    pm.collectionVariables.set('access_token', jsonData.access_token);
}
```

### **Business Logic Validation**
```javascript
pm.test('Token expires in reasonable time', function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.expires_in).to.be.above(3000); // At least 50 minutes
});
```

## 🔄 **Running Collection Tests**

### **Option 1: Collection Runner**

1. Click **Collection Runner** (⏯️ icon)
2. Select **TraceOne Monitoring API**
3. Select **TraceOne Development Environment**
4. Click **Run TraceOne Monitoring API**
5. View test results and reports

### **Option 2: Newman (Command Line)**

```bash
# Install Newman
npm install -g newman

# Run collection
newman run TraceOne_Monitoring_API.postman_collection.json \
    -e TraceOne_Environments.postman_environment.json \
    --reporters cli,html \
    --reporter-html-export ./test-results.html
```

### **Option 3: Individual Request Testing**

- Select any request
- Click **Send**
- View **Test Results** tab
- Check **Console** for detailed logs

## 📊 **Test Results and Reporting**

### **Console Output**
```
Running request: Get Access Token
Access token stored: eyJ0eXAiOiJKV1QiLCJhb...
Notifications pulled: 5

✓ Status code is 200
✓ Response has access_token
✓ Token expires in reasonable time
```

### **Test Summary**
- **Passed**: ✅ Tests that succeeded
- **Failed**: ❌ Tests that failed with details
- **Skipped**: ⏭️ Tests that were skipped

## 🐛 **Debugging and Troubleshooting**

### **Common Issues**

#### **Authentication Failures**
```
Error: 401 Unauthorized
Solution: 
- Verify client_id and client_secret
- Check if credentials are active
- Ensure base_url is correct
```

#### **Invalid DUNS Numbers**
```
Error: 400 Bad Request - Invalid DUNS
Solution:
- DUNS must be exactly 9 digits
- Use test DUNS: 123456789, 987654321, 555666777
```

#### **Rate Limiting**
```
Error: 429 Too Many Requests
Solution:
- Add delays between requests
- Use batch operations where possible
- Check rate limits in environment
```

### **Debug Tips**

1. **Enable Console Logging**
   ```javascript
   console.log('Request URL:', pm.request.url.toString());
   console.log('Response Body:', pm.response.text());
   ```

2. **Check Environment Variables**
   ```javascript
   console.log('Access Token:', pm.environment.get('access_token'));
   console.log('Base URL:', pm.environment.get('base_url'));
   ```

3. **Validate Request Data**
   ```javascript
   console.log('Request Body:', pm.request.body.raw);
   console.log('Headers:', pm.request.headers);
   ```

## 📈 **Performance Testing**

### **Response Time Monitoring**
```javascript
pm.test('Response time is acceptable', function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});
```

### **Load Testing with Newman**
```bash
# Run collection 10 times
newman run collection.json -e environment.json -n 10

# Run with delay between requests
newman run collection.json -e environment.json --delay-request 1000
```

## 🔒 **Security Best Practices**

### **Credential Management**
- Never commit credentials to version control
- Use environment variables for sensitive data
- Rotate credentials regularly
- Use different environments for testing/production

### **Token Handling**
- Tokens expire automatically (check `expires_in`)
- Store tokens securely in environment variables
- Implement automatic token refresh

## 📝 **Creating Custom Tests**

### **Add Custom Validation**
```javascript
pm.test('Registration contains required data blocks', function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.dataBlocks).to.include('companyinfo_L2_v1');
    pm.expect(jsonData.dataBlocks).to.include('principalscontacts_L1_v1');
});
```

### **Business Logic Tests**
```javascript
pm.test('Portfolio has expected number of companies', function () {
    var jsonData = pm.response.json();
    var expectedCount = pm.environment.get('expected_duns_count');
    pm.expect(jsonData.subjects.length).to.eql(parseInt(expectedCount));
});
```

## 📚 **Additional Resources**

### **TraceOne API Documentation**
- [TraceOne Direct+ API Guide](https://directplus.documentation.dnb.com/)
- [Authentication Guide](https://directplus.documentation.dnb.com/html/pages/AuthenticationGuide.html)
- [Monitoring API Reference](https://directplus.documentation.dnb.com/html/pages/MonitoringAPIReference.html)

### **Postman Resources**
- [Postman Learning Center](https://learning.postman.com/)
- [Writing Tests in Postman](https://learning.postman.com/docs/writing-scripts/test-scripts/)
- [Newman CLI Runner](https://learning.postman.com/docs/running-collections/using-newman-cli/)

## 🆘 **Support**

If you encounter issues with the Postman collection:

1. **Check Environment Variables** - Ensure all required variables are set
2. **Verify Credentials** - Confirm client_id and client_secret are valid
3. **Review Console Output** - Look for detailed error messages
4. **Check API Status** - Run Health Check requests first
5. **Update Collection** - Ensure you have the latest version

---

**Happy Testing!** 🎉

This Postman collection provides comprehensive testing capabilities for the TraceOne monitoring system, from basic authentication to complex portfolio management workflows.
