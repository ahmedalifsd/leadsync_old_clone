import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const PrivacyPolicy = () => {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <div className="flex-1">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h1 className="text-4xl font-bold mb-8" style={{ color: '#092C4C' }}>
            Privacy Policy
          </h1>

          <div className="prose prose-lg max-w-none space-y-6">
            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                1. Introduction
              </h2>
              <p className="text-gray-700">
                LeadSync (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;, or &quot;Company&quot;) operates the LeadSync.com website and associated services. This page informs you of our policies regarding the collection, use, and disclosure of personal data when you use our Service and the choices you have associated with that data.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                2. Information Collection and Use
              </h2>
              <p className="text-gray-700">
                We collect several different types of information for various purposes to provide and improve our Service to you.
              </p>
              <h3 className="text-xl font-semibold mt-4 mb-2">Types of Data Collected:</h3>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>Personal Data: Email address, First name and last name, Phone number, Address, State, Province, ZIP/Postal code, City, Cookie and Usage Data</li>
                <li>Usage Data: Pages visited, Time and date of visit, Time spent on pages, Referral source</li>
                <li>Device Information: Browser type, Operating system, Device type</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                3. Use of Data
              </h2>
              <p className="text-gray-700">
                LeadSync uses the collected data for various purposes:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>To provide and maintain our Service</li>
                <li>To notify you about changes to our Service</li>
                <li>To allow you to participate in interactive features of our Service when you choose to do so</li>
                <li>To provide customer support</li>
                <li>To gather analysis or valuable information so we can improve our Service</li>
                <li>To monitor the usage of our Service</li>
                <li>To detect, prevent and address technical issues</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                4. Security of Data
              </h2>
              <p className="text-gray-700">
                The security of your data is important to us but remember that no method of transmission over the Internet or method of electronic storage is 100% secure. While we strive to use commercially acceptable means to protect your Personal Data, we cannot guarantee its absolute security.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                5. Changes to This Privacy Policy
              </h2>
              <p className="text-gray-700">
                We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the &quot;effective date&quot; at the top of this Privacy Policy.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                6. Contact Us
              </h2>
              <p className="text-gray-700">
                If you have any questions about this Privacy Policy, please contact us at:
              </p>
              <p className="text-gray-700 mt-2">
                Email: support@leadsync.com<br />
                Address: LeadSync, Pakistan
              </p>
            </section>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};
