
Sprint 3:

In this sprint I plan to deploy this project on google cloud platform. However before we do that we need to implement a few security and utility featues. Here is my raw unfiltered thought stream for sprint 3.


1. We will be sharing this app demo to other people but I don't want the public to access it. Opening the app on your browser for the first time asks user for an access code. Only if they enter a valid code are allowed to interact with the app. There will also be a button to "Request Access" which opens up a form with fields for name, phone and company. Form inputs are saved in firestore and should somehow notify me. 

2. We need to keep track of how many tokens are being used per generation so that we can calculate a cost. We need to make a modular token counting system for our generation and regeneration endpoints. We can add a section in the `masthead` header that displays tokens used in this session and total usage. 

3. We need to save every product and script generations our test users generate so we can keep track of how/what they are using this app for and what we generated for them.

4. In the product form section we will add a select demo product section that will have a dozen products that demo users can select from. This allows users to test out the generations without having to manually enter product info.

5. Google Docs integration. Allow users to export script to google docs.

6. Deploy the api & web and make sure it works as it should.

UI Bugs:
- Clicking outside of workbench doesn't deselct any reason-item. It however deselects selected lines when clicked outside. 
