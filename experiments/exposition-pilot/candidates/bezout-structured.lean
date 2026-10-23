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

theorem forced {R : Type u} [CommRing R] (a d r s w y c : R)
    (unit : a*r+d*s=1) (left : a*c=w) (right : d*c=y) :
    c=r*w+s*y := by
  calc
    c = (a*r+d*s)*c := by rw [unit, one_mul]
    _ = r*(a*c)+s*(d*c) := by ring
    _ = r*w+s*y := by rw [left, right]

theorem compatible_iff {R : Type u} [CommRing R] (a d r s w y : R)
    (unit : a*r+d*s=1) :
    (∃ c : R, a*c=w ∧ d*c=y) ↔ a*y=d*w := by
  constructor
  · rintro ⟨c, hc, hd⟩
    calc a*y = a*(d*c) := by rw [hd]
      _ = d*(a*c) := by ring
      _ = d*w := by rw [hc]
  · intro rel
    exact ⟨r*w+s*y, compatible a d r s w y unit rel⟩

theorem missing_compatibility_counterexample :
    (1:ℤ)*1+0*0=1 ∧ ¬ ∃ c : ℤ, 1*c=0 ∧ 0*c=1 := by
  simp

theorem frame_requires_product {R : Type u} [CommRing R] (x y z a d b c : R)
    (hx : a*b=x) (hy : d*c=y) (hz : d*b=z) (det : a*c-d*b=1) :
    x*y=z*(z+1) := by
  have hac : a*c=z+1 := by
    have h := (sub_eq_iff_eq_add).mp det
    rw [hz] at h
    simpa [add_comm] using h
  calc x*y = (a*b)*(d*c) := by rw [hx, hy]
    _ = (d*b)*(a*c) := by ring
    _ = z*(z+1) := by rw [hz, hac]

theorem result {R : Type u} [EuclideanDomain R] (x y z : R)
    (h : x*y = z*(z+1)) :
    ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1 := by
  classical
  let g := EuclideanDomain.gcd x z
  by_cases hg : g = 0
  · have hxz : x = 0 ∧ z = 0 := EuclideanDomain.gcd_eq_zero_iff.mp hg
    exact ⟨1, y, 0, 1, by simp [hxz.1], by simp, by simp [hxz.2], by simp⟩
  · obtain ⟨a, ha⟩ := EuclideanDomain.gcd_dvd_left x z
    obtain ⟨d, hd⟩ := EuclideanDomain.gcd_dvd_right x z
    change x = g*a at ha
    change z = g*d at hd
    let r := EuclideanDomain.gcdA x z
    let s := EuclideanDomain.gcdB x z
    have hbez : a*r+d*s=1 := by
      apply mul_left_cancel₀ hg
      calc g * (a*r+d*s) = x*r+z*s := by rw [ha, hd]; ring
        _ = g := (EuclideanDomain.gcd_eq_gcd_ab x z).symm
        _ = g*1 := (mul_one g).symm
    have hrel : a*y=d*(z+1) := by
      apply mul_left_cancel₀ hg
      calc g*(a*y) = x*y := by rw [ha]; ring
        _ = z*(z+1) := h
        _ = g*(d*(z+1)) := by rw [hd]; ring
    obtain ⟨hc₁, hc₂⟩ := compatible a d r s (z+1) y hbez hrel
    refine ⟨a,d,g,r*(z+1)+s*y, ?_, hc₂, ?_, ?_⟩
    · simpa [mul_comm] using ha.symm
    · simpa [mul_comm] using hd.symm
    · rw [hc₁, mul_comm d g, ← hd]; ring

end Candidate
