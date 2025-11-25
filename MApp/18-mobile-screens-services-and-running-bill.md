# 18 Mobile Screens - Services & Running Bill

## Objective
Enable in-stay service browsing, ordering, and live invoice view.

## Prerequisites
- Service endpoints & invoice

## Deliverables
- Screens: ServicesList, ServiceRequest, RunningBill
- Polling or push updates (WebSocket optional later)

## Suggested Steps
1. Implement ServicesList consuming hotel services API.
2. ServiceRequest posting booking service.
3. RunningBill showing invoice with periodic refresh.
4. Add status badges for service lifecycle.

## Prompts You Can Use
- "Create Flutter services list screen with category filters." 
- "Implement service request form posting to booking services endpoint." 
- "Add running bill screen refreshing invoice totals periodically." 

## Acceptance Criteria
- User can request a service and see invoice change.
- Visual feedback for service statuses.

## Next Task
Proceed to 19 Security Hardening & Rate Limits.