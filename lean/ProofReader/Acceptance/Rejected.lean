import Lean
namespace BatchAcceptance.Rejected
/- This module deliberately tests the axiom policy. It is not mathematical evidence. -/
axiom untrusted : False
theorem must_fail : False := untrusted
theorem still_runs : True := True.intro
end BatchAcceptance.Rejected
