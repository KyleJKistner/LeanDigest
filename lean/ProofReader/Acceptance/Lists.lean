import Lean
namespace BatchAcceptance.Lists

theorem append_empty {α : Type} (xs : List α) : xs ++ [] = xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih => exact congrArg (List.cons x) ih

theorem map_append {α β : Type} (f : α → β) (xs ys : List α) :
    (xs ++ ys).map f = xs.map f ++ ys.map f := by
  induction xs with
  | nil => rfl
  | cons x xs ih => exact congrArg (List.cons (f x)) ih
-- List.recOn also has a different major-argument position from List.rec.
theorem append_empty_recOn {α : Type} (xs : List α) : xs ++ [] = xs :=
  List.recOn xs (motive := fun ys => ys ++ [] = ys) rfl
    (fun x ys ih => congrArg (List.cons x) ih)
end BatchAcceptance.Lists
