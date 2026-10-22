import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem forcedSolution {R : Type*} [CommRing R] (a d r s w y c : R)
    (hunit : a*r+d*s=1) (ha : a*c=w) (hd : d*c=y) : c=r*w+s*y := by
  calc c = (a*r+d*s)*c := by rw [hunit, one_mul]
    _ = r*(a*c)+s*(d*c) := by ring
    _ = r*w+s*y := by rw [ha, hd]

theorem compatiblePair {R : Type*} [CommRing R] (a d r s w y : R)
    (hunit : a*r+d*s=1) (hcompat : a*y=d*w) :
    a*(r*w-s*y)=w ∧ d*(r*w-s*y)=y := by
  constructor
  · calc a*(r*w+s*y) = a*r*w+s*(a*y) := by ring
      _ = (a*r+d*s)*w := by rw [hcompat]; ring
      _ = w := by rw [hunit, one_mul]
  · calc d*(r*w+s*y) = r*(d*w)+d*s*y := by ring
      _ = (a*r+d*s)*y := by rw [← hcompat]; ring
      _ = y := by rw [hunit, one_mul]

theorem frameNecessary {R : Type*} [CommRing R] (a d b c x y z : R)
    (hab : a*b=x) (hdc : d*c=y) (hdb : d*b=z) (hdet : a*c-d*b=1) :
    x*y=z*(z+1) := by
  have hac : a*c = z+1 := by
    calc a*c = (a*c-d*b)+d*b := by ring
      _ = z+1 := by rw [hdet,hdb]; ring
  calc x*y = (a*b)*(d*c) := by rw [hab,hdc]
    _ = (d*b)*(a*c) := by ring
    _ = z*(z+1) := by rw [hdb,hac]

theorem result {R : Type*} [EuclideanDomain R] (x y z : R)
    (h : x*y = z*(z+1)) :
    ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1 := by
  classical
  let g := EuclideanDomain.gcd x z
  by_cases hg : g = 0
  · obtain ⟨hx, hz⟩ := EuclideanDomain.gcd_eq_zero_iff.mp hg
    exact ⟨1,y,0,1,by simp [hx],by simp,by simp [hz],by simp⟩
  · obtain ⟨a, ha⟩ := EuclideanDomain.gcd_dvd_left x z
    obtain ⟨d, hd⟩ := EuclideanDomain.gcd_dvd_right x z
    change x=g*a at ha
    change z=g*d at hd
    let r := EuclideanDomain.gcdA x z
    let s := EuclideanDomain.gcdB x z
    have hunit : a*r+d*s=1 := by
      apply mul_left_cancel₀ hg
      calc g*(a*r+d*s) = x*r+z*s := by rw [ha,hd]; ring
        _ = g := (EuclideanDomain.gcd_eq_gcd_ab x z).symm
        _ = g*1 := (mul_one g).symm
    have hcompat : a*y=d*(z+1) := by
      apply mul_left_cancel₀ hg
      calc g*(a*y) = x*y := by rw [ha]; ring
        _ = z*(z+1) := h
        _ = g*(d*(z+1)) := by rw [hd]; ring
    obtain ⟨hac, hdc⟩ := compatiblePair a d r s (z+1) y hunit hcompat
    refine ⟨a,d,g,r*(z+1)+s*y,?_,hdc,?_,?_⟩
    · rw [mul_comm,← ha]
    · rw [mul_comm,← hd]
    · rw [hac,mul_comm d g,← hd]; ring

end PilotCandidate
