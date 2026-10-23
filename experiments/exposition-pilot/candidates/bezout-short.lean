import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem compatible {R : Type u} [CommRing R] (a d r s w y : R)
    (unit : a*r+d*s=1) (rel : a*y=d*w) :
    a*(r*w+s*y)=w ∧ d*(r*w+s*y)=y := by
  constructor
  · calc
      a*(r*w+s*y) = a*r*w+s*(a*y) := by ring
      _ = (a*r+d*s)*w := by rw [rel]; ring
      _ = w := by rw [unit, one_mul]
  · calc
      d*(r*w+s*y) = r*(d*w)+d*s*y := by ring
      _ = (a*r+d*s)*y := by rw [← rel]; ring
      _ = y := by rw [unit, one_mul]

theorem result {R : Type u} [EuclideanDomain R] (x y z : R)
    (h : x*y = z*(z+1)) :
    ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1 := by
  classical
  let g := EuclideanDomain.gcd x z
  by_cases hg : g = 0
  · obtain ⟨hx,hz⟩ := EuclideanDomain.gcd_eq_zero_iff.mp hg
    exact ⟨1,y,0,1,by simp [hx],by simp,by simp [hz],by simp⟩
  · obtain ⟨a,ha⟩ := EuclideanDomain.gcd_dvd_left x z
    obtain ⟨d,hd⟩ := EuclideanDomain.gcd_dvd_right x z
    change x = g*a at ha
    change z = g*d at hd
    let r := EuclideanDomain.gcdA x z
    let s := EuclideanDomain.gcdB x z
    have hb : a*r+d*s=1 := by
      apply mul_left_cancel₀ hg
      calc
        _ = x*r+z*s := by rw [ha,hd]; ring
        _ = _ := by simpa using (EuclideanDomain.gcd_eq_gcd_ab x z).symm
    have hr : a*y=d*(z+1) := by
      apply mul_left_cancel₀ hg
      calc
        _ = x*y := by rw [ha]; ring
        _ = _ := by rw [h,hd]; ring
    obtain ⟨hc,hc'⟩ := compatible a d r s (z+1) y hb hr
    refine ⟨a,d,g,r*(z+1)+s*y,?_,hc',?_,?_⟩
    · simpa [mul_comm] using ha.symm
    · simpa [mul_comm] using hd.symm
    · rw [hc,mul_comm d _,← hd]; ring

end Candidate
