import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const TermsAndConditions = () => {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <div className="flex-1">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h1 className="text-4xl font-bold mb-8" style={{ color: '#092C4C' }}>
            Terms and Conditions
          </h1>

          <div className="prose prose-lg max-w-none space-y-6">
            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                1. Agreement to Terms
              </h2>
              <p className="text-gray-700">
                By accessing and using the LeadSync website and services, you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                2. Use License
              </h2>
              <p className="text-gray-700">
                Permission is granted to temporarily download one copy of the materials (information or software) on LeadSync for personal, non-commercial transitory viewing only. This is the grant of a license, not a transfer of title, and under this license you may not:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700 mt-4">
                <li>Modifying or copying the materials</li>
                <li>Using the materials for any commercial purpose, or for any public display</li>
                <li>Attempting to decompile or reverse engineer any software contained on LeadSync</li>
                <li>Removing any copyright or other proprietary notations from the materials</li>
                <li>Transferring the materials to another person or &quot;mirroring&quot; the materials on any other server</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                3. Disclaimer
              </h2>
              <p className="text-gray-700">
                The materials on LeadSync are provided on an &apos;as is&apos; basis. LeadSync makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties including, without limitation, implied warranties or conditions of merchantability, fitness for a particular purpose, or non-infringement of intellectual property or other violation of rights.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                4. Limitations
              </h2>
              <p className="text-gray-700">
                In no event shall LeadSync or its suppliers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption,) arising out of the use or inability to use the materials on LeadSync.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                5. Accuracy of Materials
              </h2>
              <p className="text-gray-700">
                The materials appearing on LeadSync could include technical, typographical, or photographic errors. LeadSync does not warrant that any of the materials on LeadSync are accurate, complete, or current. LeadSync may make changes to the materials contained on LeadSync at any time without notice.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                6. Links
              </h2>
              <p className="text-gray-700">
                LeadSync has not reviewed all of the sites linked to its website and is not responsible for the contents of any such linked site. The inclusion of any link does not imply endorsement by LeadSync of the site. Use of any such linked website is at the user&apos;s own risk.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                7. Modifications
              </h2>
              <p className="text-gray-700">
                LeadSync may revise these terms of service for its website at any time without notice. By using this website, you are agreeing to be bound by the then current version of these terms of service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                8. Governing Law
              </h2>
              <p className="text-gray-700">
                These terms and conditions are governed by and construed in accordance with the laws of Pakistan, and you irrevocably submit to the exclusive jurisdiction of the courts in that location.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
                9. Contact Information
              </h2>
              <p className="text-gray-700">
                If you have any questions about these Terms and Conditions, please contact us at:
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
