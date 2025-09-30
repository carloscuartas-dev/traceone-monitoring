#!/usr/bin/env python3
"""
Quick script to test DUNS list operations immediately.

Run this with: python3 run_duns_test.py
"""

import sys
import os

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from traceone_monitoring.models.registration import RegistrationConfig
from traceone_monitoring.models.notification import (
    Notification,
    NotificationElement, 
    NotificationType,
    Organization
)


def test_duns_operations():
    """Test basic DUNS operations without pytest"""
    print("🧪 Testing DUNS List Operations")
    print("=" * 50)
    
    # 1. Define a DUNS list for testing
    tech_duns = [
        "804735132",  # Apple Inc. (example)
        "069032677",  # Microsoft Corp (example)  
        "006273905",  # Amazon.com Inc (example)
        "804735052",  # Alphabet Inc (example)
        "042112940"   # Meta Platforms (example)
    ]
    
    print(f"📋 Test DUNS List ({len(tech_duns)} companies):")
    for i, duns in enumerate(tech_duns, 1):
        print(f"   {i}. DUNS {duns}")
    
    # 2. Create registration configuration
    print("\n🔧 Creating Registration Configuration...")
    try:
        config = RegistrationConfig(
            reference="TechPortfolioTest2025",
            description="Test portfolio for tech companies monitoring",
            duns_list=tech_duns,
            dataBlocks=[
                "companyinfo_L2_v1",
                "principalscontacts_L1_v1", 
                "financialstrength_L1_v1"
            ],
            jsonPathInclusion=[
                "organization.primaryName",
                "organization.registeredAddress",
                "organization.numberOfEmployees",
                "organization.annualSalesRevenue"
            ]
        )
        print("✅ Registration config created successfully!")
        print(f"   Reference: {config.reference}")
        print(f"   DUNS Count: {len(config.duns_list)}")
        print(f"   Data Blocks: {len(config.data_blocks)}")
        print(f"   Monitoring Fields: {len(config.json_path_inclusion)}")
        
    except Exception as e:
        print(f"❌ Error creating config: {e}")
        return False
    
    # 3. Test DUNS validation
    print("\n✅ Validating DUNS Numbers...")
    valid_count = 0
    for duns in tech_duns:
        is_valid = len(duns) == 9 and duns.isdigit() and duns != "000000000"
        if is_valid:
            valid_count += 1
            print(f"   ✓ {duns} - Valid")
        else:
            print(f"   ✗ {duns} - Invalid")
    
    print(f"   {valid_count}/{len(tech_duns)} DUNS numbers are valid")
    
    # 4. Create sample notifications
    print("\n📬 Creating Sample Notifications...")
    notifications = []
    
    try:
        # Apple notification - employee count change
        apple_notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns=tech_duns[0]),
            elements=[
                NotificationElement(
                    element="organization.numberOfEmployees",
                    previous="164000",
                    current="165000",
                    timestamp=datetime.utcnow()
                )
            ],
            deliveryTimeStamp=datetime.utcnow()
        )
        notifications.append(apple_notification)
        
        # Microsoft notification - name change
        microsoft_notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns=tech_duns[1]),
            elements=[
                NotificationElement(
                    element="organization.primaryName",
                    previous="Microsoft Corporation",
                    current="Microsoft Corp",
                    timestamp=datetime.utcnow()
                )
            ],
            deliveryTimeStamp=datetime.utcnow()
        )
        notifications.append(microsoft_notification)
        
        print(f"✅ Created {len(notifications)} sample notifications")
        
        # Display notification details
        for i, notification in enumerate(notifications, 1):
            print(f"   {i}. {notification.type.value} for DUNS {notification.organization.duns}")
            print(f"      Field: {notification.elements[0].element}")
            print(f"      Change: {notification.elements[0].previous} → {notification.elements[0].current}")
        
    except Exception as e:
        print(f"❌ Error creating notifications: {e}")
        return False
    
    # 5. Test DUNS filtering
    print("\n🔍 Testing DUNS Filtering...")
    
    # Filter notifications by DUNS
    apple_duns = tech_duns[0]
    apple_notifications = [n for n in notifications if n.organization.duns == apple_duns]
    
    print(f"   Notifications for Apple (DUNS {apple_duns}): {len(apple_notifications)}")
    
    # Group by DUNS
    by_duns = {}
    for notification in notifications:
        duns = notification.organization.duns
        if duns not in by_duns:
            by_duns[duns] = []
        by_duns[duns].append(notification)
    
    print(f"   Notifications grouped by DUNS: {len(by_duns)} companies have updates")
    
    # 6. Test adding new DUNS to existing config
    print("\n➕ Testing Adding New DUNS...")
    
    new_duns = ["111222333", "444555666"]  # Example new DUNS
    updated_duns_list = config.duns_list + new_duns
    
    try:
        updated_config = RegistrationConfig(
            reference=config.reference + "_Extended",
            description=config.description + " - Extended with new companies",
            duns_list=updated_duns_list,
            dataBlocks=config.data_blocks,
            jsonPathInclusion=config.json_path_inclusion
        )
        
        print(f"✅ Extended DUNS list from {len(config.duns_list)} to {len(updated_config.duns_list)}")
        print(f"   Added DUNS: {', '.join(new_duns)}")
        
    except Exception as e:
        print(f"❌ Error extending DUNS list: {e}")
        return False
    
    print("\n🎉 All DUNS tests completed successfully!")
    return True


def show_usage_examples():
    """Show practical usage examples"""
    print("\n💡 Practical Usage Examples:")
    print("=" * 50)
    
    print("1. Running with pytest:")
    print("   pytest test_duns_example.py -v")
    print("   pytest test_duns_example.py::TestDunsListOperations::test_registration_with_duns_list -v")
    
    print("\n2. Running specific DUNS tests:")
    print("   pytest test_duns_example.py::TestDunsListOperations::test_notification_processing_by_duns -v")
    print("   pytest test_duns_example.py::TestDunsListOperations::test_bulk_monitoring_setup -v")
    
    print("\n3. Running async tests:")
    print("   pytest test_duns_example.py -k async -v")
    
    print("\n4. Real-world DUNS numbers you might use:")
    print("   # Major tech companies (these are examples, verify actual DUNS)")
    print("   tech_companies = [")
    print("       '804735132',  # Apple Inc.")
    print("       '069032677',  # Microsoft Corp") 
    print("       '006273905',  # Amazon.com Inc.")
    print("       '878975644',  # Tesla Inc.")
    print("       '191383082',  # NVIDIA Corp")
    print("   ]")
    
    print("\n5. Common monitoring fields for DUNS:")
    print("   json_path_inclusion = [")
    print("       'organization.primaryName',")
    print("       'organization.registeredAddress',")
    print("       'organization.telephone',")
    print("       'organization.websiteAddress',")
    print("       'organization.numberOfEmployees',")
    print("       'organization.annualSalesRevenue',")
    print("       'organization.operatingStatus'")
    print("   ]")


if __name__ == "__main__":
    print("🚀 TraceOne DUNS Testing Script")
    print("=" * 50)
    
    # Run the basic test
    success = test_duns_operations()
    
    if success:
        show_usage_examples()
        print(f"\n✨ Ready to start testing with your DUNS lists!")
        print(f"   Next steps:")
        print(f"   1. Replace example DUNS with your actual company DUNS")  
        print(f"   2. Run: pytest test_duns_example.py -v")
        print(f"   3. Check the integration tests in tests/integration/")
    else:
        print(f"\n❌ Some tests failed. Check the error messages above.")
        sys.exit(1)
